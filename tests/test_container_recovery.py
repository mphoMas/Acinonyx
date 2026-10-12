"""Durable delayed-create recovery using real daemon objects and fault injection."""
import asyncio
import json

import pytest

from mas.container_recovery import ContainerJournal, DurableContainerOperation, reconcile_pending
from mas.pm.adapters.boundary import ContainerBoundary
from mas.pm.adapters.antigravity import AntigravityExecutionAdapter
from mas.pm.worker import AdapterExecutionRequest
from mas.swarm.contracts import Limits, SwarmError
from mas.swarm.worker import DockerWorker


@pytest.mark.parametrize('namespace', ['coordinator', 'swarm'])
def test_delayed_create_restart_and_repeated_janitor(namespace, coordinator_test_image, tmp_path):
    async def run():
        journal = ContainerJournal()
        host = ContainerBoundary(coordinator_test_image, journal=journal) if namespace == 'coordinator' else DockerWorker(coordinator_test_image, Limits(), journal=journal)
        actual = host._docker
        saved = []
        calls = []
        async def lost_create(*args, **kwargs):
            calls.append(args[0])
            if args[0] == 'create':
                rows = journal.records(namespace=namespace)
                assert len(rows) == 1 and rows[0]['state'] == 'CREATING'
                saved.append(args)
                raise TimeoutError('Injected lost create acknowledgement')
            return await actual(*args, **kwargs)
        host._docker = lost_create
        with pytest.raises(SwarmError, match='unacknowledged'):
            if namespace == 'coordinator':
                await host._execute(['python','-c',"print('must not start')"], {}, {}, 10, None,
                                    {'run_id':'delayed','tenant':'tenant','generation':2}, None)
            else:
                await host.evaluate('def solve(x): return x', 1, 'delayed', tenant='tenant', generation=2)
        assert 'start' not in calls
        record = journal.records()[0]
        assert record['state'] == 'UNKNOWN_CREATE' and record['container_id'] is None
        restarted = ContainerJournal(journal.path)
        # Even many empty snapshots cannot settle this unknown operation.
        for _ in range(3):
            outcomes = await reconcile_pending(restarted, actual, namespace=namespace, tenant='tenant', run_id='delayed')
            assert outcomes[0]['state'] == 'UNRESOLVED'
        with pytest.raises(SwarmError, match='blocked'):
            restarted.prepare(namespace,'delayed',coordinator_test_image,tenant='tenant',generation=2)
        with pytest.raises(SwarmError, match='Unresolved'):
            restarted.prepare(namespace,'delayed',coordinator_test_image,tenant='tenant',generation=3)
        # Deliver the pending daemon request after the client/first cleanup exited.
        code, out, _ = await actual(*saved[0])
        assert code == 0
        container = out.decode().strip()
        try:
            code, raw, _ = await actual('inspect',container)
            assert code == 0 and json.loads(raw)[0]['State']['Status'] == 'created'
            results = await reconcile_pending(restarted, actual, namespace=namespace, tenant='tenant', run_id='delayed')
            assert results == [{'operation_id':record['operation_id'],'state':'CLOSED'}]
            assert await reconcile_pending(restarted, actual, namespace=namespace, tenant='tenant', run_id='delayed') == []
            code, out, _ = await actual('ps','--all','--quiet','--filter',f'name=^/{record["name"]}$')
            assert code == 0 and not out.strip()
            # Reconciliation does not itself grant another execution or restore funding.
            with pytest.raises(SwarmError, match='blocked'):
                restarted.prepare(namespace,'delayed',coordinator_test_image,tenant='tenant',generation=2)
            assert restarted.prepare(namespace,'delayed',coordinator_test_image,tenant='tenant',generation=3)['state'] == 'PREPARED'
        finally:
            await actual('rm','--force',container)
    asyncio.run(run())


def test_crash_before_send_and_cancellation_prevent_stale_start(coordinator_test_image):
    async def run():
        journal = ContainerJournal()
        host = ContainerBoundary(coordinator_test_image,journal=journal)
        record = journal.prepare('coordinator','before-send',coordinator_test_image)
        journal.cancel_run('coordinator','local','before-send')
        with pytest.raises(SwarmError, match='revoked'):
            journal.begin_create(record['operation_id'])
        assert journal.get(record['operation_id'])['state'] == 'CLOSED'
        record = journal.prepare('coordinator','stale-start',coordinator_test_image,generation=2)
        operation = DurableContainerOperation(journal,host._docker,record)
        await operation.create(['--name',operation.name,'--network=none',coordinator_test_image,'python','-c','pass'])
        journal.cancel_run('coordinator','local','stale-start')
        with pytest.raises(SwarmError, match='revoked'):
            operation.allow_start()
        await operation.cleanup()
        assert journal.get(record['operation_id'])['state'] == 'CLOSED'
    asyncio.run(run())


def test_foreign_container_is_never_removed_and_daemon_loss_stays_pending(coordinator_test_image):
    async def run():
        journal = ContainerJournal()
        host = ContainerBoundary(coordinator_test_image,journal=journal)
        record = journal.prepare('coordinator','ownership',coordinator_test_image,tenant='tenant')
        journal.begin_create(record['operation_id'])
        journal.retire(record['operation_id'],uncertain=True)
        # Same name/image but without private operation ownership labels.
        rc, out, _ = await host._docker('create','--name',record['name'],coordinator_test_image,'python','-c','pass')
        assert rc == 0
        foreign = out.decode().strip()
        try:
            assert (await reconcile_pending(journal,host._docker))[0]['state'] == 'UNRESOLVED'
            rc, _, _ = await host._docker('inspect',foreign)
            assert rc == 0
            async def offline(*args,**kwargs):
                raise SwarmError('Daemon unavailable')
            assert (await reconcile_pending(journal,offline))[0]['state'] == 'UNRESOLVED'
            assert journal.get(record['operation_id'])['state'] == 'UNKNOWN_CREATE'
        finally:
            await host._docker('rm','--force',foreign)
    asyncio.run(run())


def test_one_janitor_does_not_kill_active_or_other_tenant_containers(coordinator_test_image):
    async def run():
        journal = ContainerJournal()
        host = ContainerBoundary(coordinator_test_image,journal=journal)
        operations = []
        try:
            for tenant in ['one','two']:
                record = journal.prepare('coordinator','same-run',coordinator_test_image,tenant=tenant)
                op = DurableContainerOperation(journal,host._docker,record)
                await op.create(['--name',op.name,coordinator_test_image,'python','-c','pass'])
                operations.append(op)
            journal.cancel_run('coordinator','one','same-run')
            results = await reconcile_pending(journal,host._docker,namespace='coordinator',tenant='one',run_id='same-run')
            assert len(results) == 1 and results[0]['state'] == 'CLOSED'
            assert journal.get(operations[1].operation)['state'] == 'CREATED'
            rc, _, _ = await host._docker('inspect',operations[1].name)
            assert rc == 0
        finally:
            for op in operations:
                await op.cleanup()
    asyncio.run(run())


def test_revocation_after_create_prevents_execution(coordinator_test_image):
    async def run():
        journal = ContainerJournal()
        host = ContainerBoundary(coordinator_test_image,journal=journal)
        record = journal.prepare('coordinator','revoked',coordinator_test_image)
        operation = DurableContainerOperation(journal,host._docker,record)
        await operation.create(['--name',operation.name,coordinator_test_image,'python','-c','pass'])
        try:
            with pytest.raises(SwarmError,match='authority'):
                operation.allow_start(lambda: False)
            assert journal.get(record['operation_id'])['state'] == 'CLEANUP_PENDING'
        finally:
            await operation.cleanup()
    asyncio.run(run())


def test_unsafe_journal_paths_and_generations_rejected(tmp_path):
    target = tmp_path/'target'
    target.write_text('not a journal')
    link = tmp_path/'journal'
    link.symlink_to(target)
    with pytest.raises(SwarmError):
        ContainerJournal(link)
    journal = ContainerJournal()
    for generation in (True,0,-1,1.5):
        with pytest.raises(SwarmError):
            journal.prepare('swarm','run','sha256:'+'a'*64,generation=generation)


def test_adapter_uncertainty_does_not_settle_funded_pm_attempt(coordinator_test_image,tmp_path):
    from mas.pm.coordinator import trusted_coordinator_admin_scope
    from mas.pm.db import PMDatabase
    from mas.pm.models import Project, Issue
    db=PMDatabase(tmp_path/'pm.db')
    db.create_project(Project(id='p',key='P',name='Project',token_budget=1000))
    db.create_issue(Issue(id='i',project_id='p',key='P-1',title='Task'))
    with db.atomic_transaction() as conn:
        conn.execute("INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p','T','task','i','P-1')")
    with trusted_coordinator_admin_scope():
        store=db.coordinator
        store.create_attempt_with_intent('a','intent','tenant','p','i','task',1,'antigravity',{},budget_reservation=100)
        assert store.claim_intent('intent','worker',1,100,30)
        assert store.pre_spawn_intent('intent','worker',2,101,'run','a')
        (tmp_path/'source.py').write_text('pass')
        runtime=AntigravityExecutionAdapter(image=coordinator_test_image,simulate_command=['python','-c','pass'])
        actual=runtime.boundary._docker
        async def lost(*args,**kwargs):
            if args[0]=='create':
                raise TimeoutError('Lost ACK')
            return await actual(*args,**kwargs)
        runtime.boundary._docker=lost
        req=AdapterExecutionRequest('tenant','p','i','task','a',1,2,'antigravity','fixture',workspace_path=str(tmp_path),path_whitelist=['source.py'])
        result=runtime.execute(req,'run')
        assert result.status=='UNKNOWN_EXECUTION' and result.tokens_billed is None
        assert store.record_execution_interrupted('intent','worker',2)
        with db._get_connection() as conn:
            assert conn.execute('SELECT status,amount,settled_amount FROM pm_coordinator_reservations').fetchone()[:] == ('HELD',100,0)
            assert conn.execute('SELECT tokens_consumed FROM pm_projects').fetchone()[0]==0
    assert ContainerJournal().records()[0]['state']=='UNKNOWN_CREATE'


def test_process_death_before_ack_survives_and_cannot_launch(coordinator_test_image,tmp_path):
    import subprocess
    import sys
    journal=ContainerJournal()
    child = '''import os,sys
from mas.container_recovery import ContainerJournal
j=ContainerJournal(sys.argv[1])
r=j.prepare('coordinator','process-death',sys.argv[2],tenant='tenant',generation=3)
j.begin_create(r['operation_id'])
os._exit(17)
'''
    result=subprocess.run([sys.executable,'-c',child,str(journal.path),coordinator_test_image],capture_output=True)
    assert result.returncode==17
    restarted=ContainerJournal(journal.path)
    record=restarted.records()[0]
    assert record['state']=='CREATING'
    host=ContainerBoundary(coordinator_test_image,journal=restarted)
    with pytest.raises(SwarmError,match='unresolved'):
        asyncio.run(host.recover('process-death',tenant='tenant'))
    assert restarted.get(record['operation_id'])['state']=='UNKNOWN_CREATE'
    with pytest.raises(SwarmError,match='revoked'):
        restarted.begin_start(record['operation_id'])


def test_recovery_script_does_not_report_unresolved_absence_as_success(coordinator_test_image):
    import subprocess
    import sys
    journal=ContainerJournal()
    record=journal.prepare('coordinator','cli-unknown',coordinator_test_image)
    journal.begin_create(record['operation_id'])
    journal.retire(record['operation_id'],uncertain=True)
    result=subprocess.run([sys.executable,'scripts/reconcile_container_recovery.py','--journal',str(journal.path),
                           '--namespace','coordinator','--tenant','local','--run-id','cli-unknown'],capture_output=True,text=True)
    assert result.returncode==1
    assert json.loads(result.stdout)['unresolved']==1
    assert ContainerJournal(journal.path).get(record['operation_id'])['state']=='UNKNOWN_CREATE'


def test_two_janitors_reconcile_same_owned_operation_safely(coordinator_test_image):
    async def run():
        journal=ContainerJournal()
        host=ContainerBoundary(coordinator_test_image,journal=journal)
        record=journal.prepare('coordinator','two-janitors',coordinator_test_image)
        operation=DurableContainerOperation(journal,host._docker,record)
        await operation.create(['--name',operation.name,coordinator_test_image,'python','-c','pass'])
        journal.retire(record['operation_id'],uncertain=True)
        try:
            first,second=await asyncio.gather(reconcile_pending(journal,host._docker),reconcile_pending(ContainerJournal(journal.path),host._docker))
            # One reader can truthfully see deletion in progress. It must never
            # fabricate success; the final durable state and next pass converge.
            assert all(r['state'] in {'CLOSED','UNRESOLVED'} for batch in (first,second) for r in batch)
            assert any(r['state']=='CLOSED' for batch in (first,second) for r in batch)
            assert journal.get(record['operation_id'])['state']=='CLOSED'
            assert await reconcile_pending(journal,host._docker)==[]
        finally:
            await host._docker('rm','--force',operation.name)
    asyncio.run(run())
