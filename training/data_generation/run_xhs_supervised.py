"""
Auto-restart supervisor for safe_collect_from_xhs.py.

Why this exists:
- Playwright may occasionally hang at runtime.
- The collector already supports --append checkpoint resume.
- This supervisor kills/restarts the collector when it is stuck
  (no output/checkpoint/run-log updates for a configurable duration).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _arg_value(args: Sequence[str], name: str) -> Optional[str]:
    for i, a in enumerate(args):
        if a == name:
            if i + 1 < len(args):
                return args[i + 1]
            return None
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def _has_flag(args: Sequence[str], flag: str) -> bool:
    return any(a == flag for a in args)


def _add_kv(args: List[str], name: str, value: str) -> None:
    args.extend([name, value])


def _resolve_path(base_dir: Path, p: str) -> Path:
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _latest_mtime(paths: Sequence[Path]) -> float:
    mtimes = []
    for p in paths:
        try:
            if p.exists():
                mtimes.append(p.stat().st_mtime)
        except Exception:
            continue
    return max(mtimes) if mtimes else 0.0


def _count_running_collectors() -> int:
    """
    Count running safe_collect_from_xhs.py processes.
    Used to avoid killing other collector's active Playwright Chrome when running A/B in parallel.
    """
    if os.name != "nt":
        return 0
    try:
        result = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                "name='python.exe' and CommandLine like '%safe_collect_from_xhs.py%'",
                "get",
                "ProcessId",
                "/format:list",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            errors="ignore",
            check=False,
        )
        cnt = 0
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("ProcessId="):
                pid_str = line.split("=", 1)[1].strip()
                if pid_str.isdigit():
                    cnt += 1
        return cnt
    except Exception:
        return 0


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        # 仅当没有其他 collector 在跑时，才杀 ms-playwright Chrome，避免 A/B 并行互相误杀。
        time.sleep(2)
        if _count_running_collectors() == 0:
            _kill_playwright_orphan_chromes()
    else:
        try:
            os.killpg(os.getpgid(pid), 9)
        except Exception:
            pass


def _kill_playwright_orphan_chromes() -> None:
    """结束路径含 ms-playwright 的孤儿 chrome.exe 进程，避免 OOM 累积。"""
    try:
        result = subprocess.run(
            [
                "wmic", "process", "where",
                "name='chrome.exe' and ExecutablePath like '%ms-playwright%'",
                "get", "ProcessId", "/format:list",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            errors="ignore",
            check=False,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("ProcessId="):
                pid_str = line.split("=", 1)[1].strip()
                if pid_str.isdigit():
                    subprocess.run(
                        ["taskkill", "/PID", pid_str, "/F"],
                        capture_output=True,
                        check=False,
                    )
                    print(f"[{_now()}] [supervisor] killed orphan chrome pid={pid_str}", flush=True)
    except Exception:
        pass


def _launch_collector(
    python_exe: Path,
    collector_script: Path,
    collector_args: Sequence[str],
    working_dir: Path,
) -> subprocess.Popen:
    cmd = [str(python_exe), str(collector_script), *collector_args]
    print(f"[{_now()}] [supervisor] start: {subprocess.list2cmdline(cmd)}", flush=True)
    return subprocess.Popen(cmd, cwd=str(working_dir))


def _monitor_until_exit_or_stuck(
    proc: subprocess.Popen,
    activity_files: Sequence[Path],
    stuck_seconds: int,
    poll_seconds: int,
) -> Tuple[str, Optional[int], int]:
    # IMPORTANT:
    # If activity_files already exist but are old (from a previous run), using their mtime directly
    # would cause an immediate "stuck" detection on startup. We treat "now" as the initial baseline.
    now0 = time.time()
    last_activity_ts = max(now0, _latest_mtime(activity_files))
    last_heartbeat_print = 0.0

    while True:
        rc = proc.poll()
        now = time.time()
        latest = _latest_mtime(activity_files)
        if latest > last_activity_ts:
            last_activity_ts = latest
        idle_sec = int(max(0.0, now - last_activity_ts))

        if rc is not None:
            return ("exit", int(rc), idle_sec)

        if idle_sec >= stuck_seconds:
            return ("stuck", None, idle_sec)

        if now - last_heartbeat_print >= max(60.0, float(poll_seconds * 3)):
            print(
                f"[{_now()}] [supervisor] pid={proc.pid} alive idle={idle_sec}s",
                flush=True,
            )
            last_heartbeat_print = now

        time.sleep(max(2, int(poll_seconds)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-restart wrapper for safe_collect_from_xhs.py (anti-hang supervisor)."
    )
    parser.add_argument(
        "--python-exe",
        type=str,
        default=sys.executable,
        help="Python executable used to run collector.",
    )
    parser.add_argument(
        "--collector-script",
        type=str,
        default="training/data_generation/safe_collect_from_xhs.py",
        help="Collector script path.",
    )
    parser.add_argument(
        "--working-dir",
        type=str,
        default=".",
        help="Working directory for collector process.",
    )
    parser.add_argument(
        "--stuck-seconds",
        type=int,
        default=900,
        help="Restart when no activity file update for this many seconds.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=15,
        help="Watchdog poll interval seconds.",
    )
    parser.add_argument(
        "--restart-delay-seconds",
        type=int,
        default=8,
        help="Sleep seconds before restarting collector.",
    )
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=50,
        help="Maximum auto restarts before giving up.",
    )
    parser.add_argument(
        "--no-auto-append",
        action="store_true",
        help="Do not auto-inject --append when missing.",
    )
    parser.add_argument(
        "--allow-nonzero-exit",
        action="store_true",
        help="Exit supervisor when collector exits non-zero (disable auto restart on errors).",
    )
    parser.add_argument(
        "collector_args",
        nargs=argparse.REMAINDER,
        help="Arguments for collector. Use '--' before collector args.",
    )
    args = parser.parse_args()
    if args.collector_args and args.collector_args[0] == "--":
        args.collector_args = args.collector_args[1:]
    return args


def main() -> int:
    args = parse_args()
    collector_args = list(args.collector_args or [])

    working_dir = Path(args.working_dir).resolve()
    python_exe = _resolve_path(working_dir, args.python_exe)
    collector_script = _resolve_path(working_dir, args.collector_script)

    output_value = _arg_value(collector_args, "--output")
    if not output_value:
        raise SystemExit("collector_args 必须显式提供 --output，避免重启时写入到不同文件。")
    output_path = _resolve_path(working_dir, output_value)

    if not args.no_auto_append and not _has_flag(collector_args, "--append"):
        collector_args.append("--append")
        print(f"[{_now()}] [supervisor] auto add --append", flush=True)

    run_log_value = _arg_value(collector_args, "--run-log-file")
    if run_log_value:
        run_log_path = _resolve_path(working_dir, run_log_value)
    else:
        run_log_path = output_path.parent / f"{output_path.stem}.run.log"
        _add_kv(collector_args, "--run-log-file", str(run_log_path))
        print(f"[{_now()}] [supervisor] auto add --run-log-file {run_log_path}", flush=True)

    storage_state_value = _arg_value(collector_args, "--storage-state-file")
    if not storage_state_value:
        default_state = working_dir / "training" / "data" / "raw" / "xhs_auth_state.json"
        _add_kv(collector_args, "--storage-state-file", str(default_state))
        print(f"[{_now()}] [supervisor] auto add --storage-state-file {default_state}", flush=True)

    checkpoint_path = output_path.parent / f"{output_path.stem}.checkpoint.json"
    activity_files = [output_path, run_log_path, checkpoint_path]
    print(
        f"[{_now()}] [supervisor] activity files: "
        + ", ".join(str(p) for p in activity_files),
        flush=True,
    )

    restart_count = 0
    current_proc: Optional[subprocess.Popen] = None
    try:
        while True:
            # 启动前先清一次孤儿 Chrome（仅当没有其他 collector 在跑时）
            if _count_running_collectors() == 0:
                _kill_playwright_orphan_chromes()
            current_proc = _launch_collector(
                python_exe=python_exe,
                collector_script=collector_script,
                collector_args=collector_args,
                working_dir=working_dir,
            )
            reason, rc, idle_sec = _monitor_until_exit_or_stuck(
                proc=current_proc,
                activity_files=activity_files,
                stuck_seconds=max(60, int(args.stuck_seconds)),
                poll_seconds=max(2, int(args.poll_seconds)),
            )

            if reason == "exit" and rc == 0:
                print(f"[{_now()}] [supervisor] collector exit=0, done.", flush=True)
                return 0

            if reason == "exit":
                print(
                    f"[{_now()}] [supervisor] collector exit={rc} idle={idle_sec}s",
                    flush=True,
                )
                if int(rc or 0) == 42:
                    # rate-limit stop: do not immediately restart and hammer again
                    cool = max(600, int(args.stuck_seconds))
                    cool = max(cool, 1800)
                    print(f"[{_now()}] [supervisor] rate-limited exit, cooldown {cool}s before restart", flush=True)
                    time.sleep(cool)
                elif int(rc or 0) == 43:
                    # planned restart (memory hygiene)
                    pass
                if args.allow_nonzero_exit:
                    return int(rc or 1)
            else:
                print(
                    f"[{_now()}] [supervisor] stuck detected (idle={idle_sec}s), killing pid={current_proc.pid}",
                    flush=True,
                )
                _kill_process_tree(current_proc.pid)

            restart_count += 1
            if restart_count > int(args.max_restarts):
                print(
                    f"[{_now()}] [supervisor] max restarts exceeded ({args.max_restarts}), abort.",
                    flush=True,
                )
                return 1

            print(
                f"[{_now()}] [supervisor] restart #{restart_count} in {args.restart_delay_seconds}s",
                flush=True,
            )
            time.sleep(max(0, int(args.restart_delay_seconds)))
    except KeyboardInterrupt:
        print(f"[{_now()}] [supervisor] interrupted by user", flush=True)
        if current_proc is not None and current_proc.poll() is None:
            _kill_process_tree(current_proc.pid)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

