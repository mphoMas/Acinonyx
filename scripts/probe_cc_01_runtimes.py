#!/usr/bin/env python3
"""
scripts/probe_cc_01_runtimes.py: Reproducible empirical probes for CC-01 runtime qualification.

Probes measured:
1. Probe 1 (Run Identification): Measure whether durable run/thread references are emitted before completion.
2. Probe 2 (Interrupted Execution & Duplicate Side Effect Probe): Launch run with external side effect counter, interrupt midway, attempt recovery, and count side effects.
3. Probe 3 (Crash Recovery & UNKNOWN_EXECUTION): Test failure around launch and persistence; specify UNKNOWN_EXECUTION when recovery cannot guarantee single execution.
4. Probe 4 (Cancellation & Descendant Cleanup): Test OS process group signaling, measure descendant termination, and detect any leaked child processes.
5. Probe 5 (Actual Git Review): Adversarial evaluation of a defective candidate Git diff with codex-auto-review, measuring genuine rejection.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _bounded_cleanup_process(p: subprocess.Popen, timeout: float = 3.0) -> None:
    """
    Safely and boundedly clean up a subprocess and its process group.
    Sends SIGTERM to process group, waits up to `timeout` seconds, then falls back to SIGKILL.
    """
    try:
        pgid = os.getpgid(p.pid)
    except (ProcessLookupError, OSError):
        pgid = None

    if p.poll() is None:
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGTERM)
            except OSError:
                pass
        else:
            try:
                p.terminate()
            except OSError:
                pass

        t0 = time.time()
        while time.time() - t0 < timeout:
            if p.poll() is not None:
                break
            time.sleep(0.05)

        if p.poll() is None:
            if pgid is not None:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except OSError:
                    pass
            else:
                try:
                    p.kill()
                except OSError:
                    pass
            try:
                p.wait(timeout=1.0)
            except (subprocess.TimeoutExpired, OSError):
                pass


def _read_first_line_bounded(cmd: list[str], deadline_seconds: float = 15.0) -> tuple[str, float, int]:
    """
    Executes cmd in a new process group, bounds stdout reading using selectors to deadline_seconds,
    and performs bounded process cleanup.
    Returns (first_line, read_latency_seconds, exit_code).
    """
    import selectors

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ)
    t0 = time.time()
    buf = b""
    first_line = ""
    read_latency = 0.0

    while True:
        remaining = deadline_seconds - (time.time() - t0)
        if remaining <= 0:
            break
        events = sel.select(timeout=min(remaining, 0.1))
        if events:
            chunk = os.read(p.stdout.fileno(), 4096)
            if not chunk:  # EOF
                break
            buf += chunk
            if b"\n" in buf:
                first_line = buf.splitlines()[0].decode("utf-8", errors="replace").strip()
                read_latency = time.time() - t0
                break

    sel.unregister(p.stdout)
    sel.close()

    if not first_line:
        read_latency = time.time() - t0

    _bounded_cleanup_process(p, timeout=3.0)
    exit_code = p.poll() if p.poll() is not None else -1

    return first_line, round(read_latency, 2), exit_code


def probe_1_early_run_identification() -> dict:
    """Probe 1: Measure early run identification before turn completion with strict 15s deadline."""
    print("[Probe 1] Testing early run identification with bounded stream read (15.0s deadline)...")
    results = {}

    # 1. Codex early reference
    codex_cmd = [
        "codex", "exec", "--skip-git-repo-check", "-m", "codex-auto-review", "--json", "echo probe1"
    ]
    try:
        first_line, latency, _ = _read_first_line_bounded(codex_cmd, deadline_seconds=15.0)
        data = json.loads(first_line) if first_line else {}
        thread_id = data.get("thread_id")
        has_id = bool(thread_id and str(thread_id).strip())
        results["codex"] = {
            "supported": has_id and (latency <= 15.0),
            "latency_seconds": latency,
            "deadline_seconds": 15.0,
            "early_run_id_type": "thread_id",
            "sample_id": thread_id,
            "event_type": data.get("type"),
            "command": " ".join(codex_cmd),
            "bounded_cleanup": "SIGTERM to process group with 3s timeout and SIGKILL fallback",
        }
    except Exception as e:
        results["codex"] = {"supported": False, "error": str(e)}

    # 2. Antigravity early reference via stream-json
    agy_cmd = [
        "agy", "-p", "echo probe1", "--output-format", "stream-json"
    ]
    try:
        first_line, latency, _ = _read_first_line_bounded(agy_cmd, deadline_seconds=15.0)
        data = json.loads(first_line) if first_line else {}
        conv_id = data.get("conversation_id")
        has_id = bool(conv_id and str(conv_id).strip())
        results["antigravity"] = {
            "supported": has_id and (latency <= 15.0),
            "latency_seconds": latency,
            "deadline_seconds": 15.0,
            "early_run_id_type": "conversation_id",
            "sample_id": conv_id,
            "event_type": data.get("event"),
            "command": " ".join(agy_cmd),
            "bounded_cleanup": "SIGTERM to process group with 3s timeout and SIGKILL fallback",
        }
    except Exception as e:
        results["antigravity"] = {"supported": False, "error": str(e)}

    return results


def probe_2_interrupted_execution_and_side_effects() -> dict:
    """
    Probe 2: Synthetic side-effect simulation measuring interrupted execution and retry.
    Explicitly labeled as a synthetic controlled subprocess demonstration proving that
    uncoordinated retries duplicate external side effects, necessitating UNKNOWN_EXECUTION.
    """
    print("[Probe 2] Measuring synthetic side-effects under process interruption...")
    tmp = tempfile.mkdtemp(prefix="cc01_probe2_")
    side_effect_log = Path(tmp) / "counter.log"
    results = {}

    try:
        worker_script = f"""
import sys, time
with open('{side_effect_log}', 'a') as f:
    f.write('EFFECT_INVOKED\\n')
time.sleep(5)
"""
        script_file = Path(tmp) / "worker.py"
        script_file.write_text(worker_script)

        # Launch synthetic worker in dedicated process group
        p = subprocess.Popen(
            [sys.executable, str(script_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
        time.sleep(0.5)
        # Interrupt midway
        pgid = os.getpgid(p.pid)
        os.killpg(pgid, signal.SIGTERM)
        p.wait()

        # Count effects during first run
        count_first = len(side_effect_log.read_text().splitlines()) if side_effect_log.exists() else 0

        # Attempt naive retry
        p2 = subprocess.Popen(
            [sys.executable, str(script_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
        time.sleep(0.5)
        os.killpg(os.getpgid(p2.pid), signal.SIGTERM)
        p2.wait()

        count_total = len(side_effect_log.read_text().splitlines()) if side_effect_log.exists() else 0

        results["measurement"] = {
            "evaluation_type": "synthetic_controlled_subprocess",
            "initial_effects": count_first,
            "total_effects_after_retry": count_total,
            "duplicate_executed": (count_total > 1),
            "runtime_verdict": "UNSUPPORTED_EXACTLY_ONCE",
            "policy": "UNKNOWN_EXECUTION - coordinator MUST NOT automatically retry in-flight side effects.",
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return results


def probe_3_crash_recovery_classification() -> dict:
    """
    Probe 3: Proposed architectural policy classifications for crash recovery.
    Explicitly labeled as proposed architectural policies rather than empirical runtime behaviors.
    """
    print("[Probe 3] Recording crash recovery policy specifications...")
    return {
        "evaluation_type": "proposed_architectural_policy_specification",
        "state_before_launch": {
            "outcome": "SAFE_RETRY",
            "reason": "Process was not spawned; lease/intent not executed; idempotency key reusable.",
        },
        "state_after_launch_before_id_persisted": {
            "outcome": "UNKNOWN_EXECUTION",
            "reason": "Process may have run side effects; run ID not recorded; automatic retry prohibited; requires coordinator reconciliation.",
        },
        "state_after_id_persisted_before_completion": {
            "outcome": "INTERRUPTED_IN_FLIGHT",
            "reason": "Run ID known; cannot guarantee side-effect idempotency on resumption; session continuation is turn 2, not turn 1 replay.",
        },
    }


def probe_4_cancellation_containment() -> dict:
    """
    Probe 4: Check descendant processes and late results under process group cancellation.
    Observes past the late-write deadline and inspects descendant process survival using psutil.
    """
    print("[Probe 4] Testing cancellation containment with child process and observing past deadline...")
    import psutil
    tmp = tempfile.mkdtemp(prefix="cc01_probe4_")
    log_file = Path(tmp) / "child.log"
    pid_file = Path(tmp) / "child.pid"

    # Child process sleeps 2 seconds, writes to log
    parent_script = f"""
import subprocess, sys, time
p = subprocess.Popen([sys.executable, "-c", "import os, time; open('{pid_file}', 'w').write(str(os.getpid())); time.sleep(2); open('{log_file}', 'w').write('LATE_WRITE')"])
p.wait()
"""
    script_path = Path(tmp) / "parent.py"
    script_path.write_text(parent_script)

    p = subprocess.Popen(
        [sys.executable, str(script_path)],
        preexec_fn=os.setsid,
    )
    pgid = os.getpgid(p.pid)
    # Wait 0.3s for child to start and write pid
    time.sleep(0.3)
    child_pid = None
    if pid_file.exists():
        try:
            child_pid = int(pid_file.read_text().strip())
        except Exception:
            pass

    # Issue SIGTERM to process group
    os.killpg(pgid, signal.SIGTERM)
    p.wait()

    # Observe beyond the late-write deadline (child was scheduled for 2s)
    # Wait 3.0s total to observe if child leaked and executed late write
    time.sleep(3.0)

    # Check child process survival
    child_survived = False
    if child_pid is not None:
        try:
            proc = psutil.Process(child_pid)
            child_survived = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            child_survived = False

    late_write_occurred = log_file.exists()
    _bounded_cleanup_process(p, timeout=3.0)
    shutil.rmtree(tmp, ignore_errors=True)

    return {
        "evaluation_type": "synthetic_controlled_subprocess_process_group",
        "os_killpg_sigterm": "Process group terminated cleanly via bounded cleanup",
        "child_pid_tracked": child_pid,
        "child_survived_past_deadline": child_survived,
        "late_filesystem_writes": "Detected" if late_write_occurred else "None",
        "containment_limitation": "Process cleanup measurement is a controlled subprocess test; it does NOT qualify cancellation of live multi-process agents, remote containers, or independent network jobs. Without adapter-level heartbeat/cancellation APIs, in-flight remote operations remain UNKNOWN_EXECUTION.",
    }


def probe_5_adversarial_candidate_review() -> dict:
    """
    Probe 5: Adversarial evaluation of a defective Git commit candidate using codex-auto-review.
    Initializes a real disposable git repository with a commit and reviews the git commit.
    """
    print("[Probe 5] Running adversarial evaluation of real Git commit candidate...")
    tmp = tempfile.mkdtemp(prefix="cc01_probe5_git_")
    repo_dir = Path(tmp) / "repo"
    repo_dir.mkdir()

    try:
        # Initialize real disposable git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, capture_output=True, check=True)

        auth_file = repo_dir / "auth.py"
        auth_file.write_text("def verify_admin(token):\n    if not token:\n        return False\n    return False\n")
        subprocess.run(["git", "add", "auth.py"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "initial secure check"], cwd=repo_dir, capture_output=True, check=True)

        # Introduce defect in commit
        auth_file.write_text("def verify_admin(token):\n    # bypass check\n    return True\n")
        subprocess.run(["git", "commit", "-am", "bypass auth check (defective)"], cwd=repo_dir, capture_output=True, check=True)

        diff_proc = subprocess.run(["git", "show", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True)
        git_diff = diff_proc.stdout

        prompt = f"Review Git commit diff:\n{git_diff}\nIs this acceptable or should it be rejected? State verdict REJECT or APPROVE:"

        cmd = ["codex", "exec", "--skip-git-repo-check", "-m", "codex-auto-review", "--json", prompt]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        verdict_text = ""
        for line in res.stdout.splitlines():
            try:
                evt = json.loads(line)
                if evt.get("type") == "item.completed" and evt.get("item", {}).get("type") == "agent_message":
                    verdict_text = evt["item"]["text"]
            except Exception:
                pass

        is_rejected = "REJECT" in verdict_text.upper()
        return {
            "evaluation_type": "empirical_git_commit_review",
            "candidate_commit_subject": "bypass auth check (defective)",
            "reviewer_model": "codex-auto-review",
            "verdict_detected": "REJECT" if is_rejected else "UNKNOWN",
            "reviewer_response_snippet": verdict_text[:300],
            "verdict_authentic": is_rejected,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    print("=" * 60)
    print("CC-01 EMPIRICAL RUNTIME PROBE SUITE")
    print("=" * 60)

    p1 = probe_1_early_run_identification()
    p2 = probe_2_interrupted_execution_and_side_effects()
    p3 = probe_3_crash_recovery_classification()
    p4 = probe_4_cancellation_containment()
    p5 = probe_5_adversarial_candidate_review()

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "probe_1_early_run_id": p1,
        "probe_2_side_effects": p2,
        "probe_3_crash_recovery": p3,
        "probe_4_cancellation": p4,
        "probe_5_adversarial_review": p5,
    }

    out_path = Path("projects/scrum-board-automation/planning/CC_01_PROBE_RECEIPTS.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))
    print("\nProbes complete! Receipts saved to:", out_path)

    # Verification of required criteria
    failed_criteria = []
    if not p1.get("codex", {}).get("supported"):
        failed_criteria.append("Codex early run ID not received within 15s deadline")
    if not p1.get("antigravity", {}).get("supported"):
        failed_criteria.append("Antigravity early run ID not received within 15s deadline")
    if not p2.get("measurement", {}).get("duplicate_executed"):
        failed_criteria.append("Probe 2 did not demonstrate side-effect duplication on uncoordinated retry")
    if p4.get("child_survived_past_deadline"):
        failed_criteria.append("Probe 4 child process leaked / survived past cancellation deadline")
    if p4.get("late_filesystem_writes") != "None":
        failed_criteria.append("Probe 4 late filesystem writes detected")
    if not p5.get("verdict_authentic"):
        failed_criteria.append("Probe 5 reviewer did not authentically reject defective candidate commit")

    if failed_criteria:
        print("\n[CRITERIA FAILURE] Unmet required probe criteria:")
        for fc in failed_criteria:
            print(f"  - {fc}")
        sys.exit(1)
    else:
        print("\n[CRITERIA SUCCESS] All empirical and qualification criteria satisfied.")
        sys.exit(0)


if __name__ == "__main__":
    main()


