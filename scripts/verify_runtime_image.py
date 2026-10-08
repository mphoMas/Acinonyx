"""Real runtime-image startup, authorization and persistent-volume restart checks."""
import argparse
import json
import os
import subprocess
import time
import uuid
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--image', required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
cmd = ['docker', '--host=unix:///var/run/docker.sock']
env = {k:v for k,v in os.environ.items() if k not in {'DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'}}
name = 'mas-runtime-audit-' + uuid.uuid4().hex[:12]
volume = name + '-state'
report = {'image': args.image, 'checks': {}}
def docker(*args):
    result = subprocess.run(cmd + list(args), env=env, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr[-1000:])
    return (result.stdout + result.stderr).strip() if args[0] == "logs" else result.stdout.strip()
def execute(code):
    return docker('exec',name,'python','-c',code)
def start():
    docker('run','--detach','--name',name,'--network=none','--read-only','--tmpfs','/tmp','--mount',f'type=volume,src={volume},dst=/app/workspace','--env','MAS_GIT_QUEUE_AUTOSYNC=false',args.image)
    for _ in range(30):
        try:
            value = execute("import urllib.request,json; o=urllib.request.build_opener(urllib.request.ProxyHandler({})); print(json.dumps(json.load(o.open('http://127.0.0.1:8080/api/status',timeout=2))))")
            assert json.loads(value)['status'] == 'active'
            return
        except (RuntimeError,AssertionError) as error:
            last_error = str(error)
            time.sleep(0.5)
    raise RuntimeError('Runtime did not become healthy: ' + last_error)
try:
    docker('volume','create',volume)
    start()
    report['image_id']=docker('image','inspect','--format','{{.Id}}',args.image)
    assert execute('import os; print(os.getuid())') == '10001'
    report['checks']['non_root_uid']=10001
    assert execute("import urllib.request; o=urllib.request.build_opener(urllib.request.ProxyHandler({})); r=o.open('http://127.0.0.1:8080/portal/index.html'); print(r.status)") == '200'
    report['checks']['portal_http']=200
    assert execute("import urllib.request,urllib.error; o=urllib.request.build_opener(urllib.request.ProxyHandler({}));\ntry: o.open(urllib.request.Request('http://127.0.0.1:8080/api/dispatch',data=b'{}'))\nexcept urllib.error.HTTPError as e: print(e.code)") == '401'
    report['checks']['unconfigured_mutation_denied']=401
    execute("from mas.pm.db import PMDatabase; from mas.pm.models import Project; PMDatabase().create_project(Project(id='audit-restart',key='AUDRESTART',name='Restart evidence'))")
    assert execute("from mas.pm.db import PMDatabase; print(PMDatabase().db_path)") == '/app/workspace/mas_pm.db'
    docker('rm','--force',name)
    start()
    assert execute("from mas.pm.db import PMDatabase; print(PMDatabase().get_project_by_key('AUDRESTART').name)") == 'Restart evidence'
    report['checks']['volume_restart_preserves_pm_project']=True
    sandbox=execute("import asyncio; from mas.tools.executor import run_python_code; print(asyncio.run(run_python_code('print(42)')))")
    if sandbox.strip() == '42':
        report['checks']['legacy_python_executor']='isolated_math_passed'
    else:
        assert 'bwrap:' in sandbox or 'Sandbox unavailable' in sandbox, sandbox
        report['checks']['legacy_python_executor']='unavailable_in_default_container; execution_refused'
    report['status']='passed'
except Exception:
    print(docker('logs',name))
    raise
finally:
    removed = subprocess.run(cmd+['rm','--force',name],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    unmounted = subprocess.run(cmd+['volume','rm',volume],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    if removed.returncode or unmounted.returncode:
        raise RuntimeError('Audit-owned container/volume cleanup failed')
    report['checks']['cleanup_confirmed'] = True
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
