#!/usr/bin/env python3
"""Host-operator janitor. Persistent UNKNOWN_CREATE records never time out to success."""
import argparse
import asyncio
import json

from mas.container_recovery import ContainerJournal, reconcile_pending
from mas.pm.adapters.boundary import ContainerBoundary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', required=True, help='Trusted private host journal path')
    parser.add_argument('--namespace', choices=['swarm', 'coordinator'])
    parser.add_argument('--tenant')
    parser.add_argument('--run-id')
    parser.add_argument('--retire-run', action='store_true', help='Explicit host-owner quarantine of the specified already-authorized run')
    parser.add_argument('--watch', action='store_true', help='Repeat until explicitly stopped; unresolved rows stay durable')
    parser.add_argument('--interval', type=float, default=5)
    args = parser.parse_args()
    if not 0.1 <= args.interval <= 60:
        parser.error('interval must be finite and between 0.1 and 60 seconds')
    if args.retire_run and (not args.namespace or not args.tenant or not args.run_id):
        parser.error('--retire-run requires namespace, tenant and run-id')
    journal = ContainerJournal(args.journal)
    if args.retire_run:
        journal.cancel_run(args.namespace, args.tenant, args.run_id)
    # Image is never executed by the janitor; each operation has its actual pin.
    control = ContainerBoundary('sha256:'+'0'*64, journal=journal)
    async def run():
        while True:
            result = await reconcile_pending(journal, control._docker, namespace=args.namespace,
                                             tenant=args.tenant, run_id=args.run_id)
            pending = bool(journal.records(namespace=args.namespace, tenant=args.tenant, run_id=args.run_id, pending_only=True, limit=1))
            print(json.dumps({'operations': result, 'unresolved': sum(r['state'] != 'CLOSED' for r in result), 'pending_remaining': pending}), flush=True)
            if not args.watch:
                return 1 if pending else 0
            await asyncio.sleep(args.interval)
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
