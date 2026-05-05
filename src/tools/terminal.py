import base64
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid

_KONSOLE_PROC = None
_JARVIS_FIFO = "/tmp/jarvis_konsole_fifo"
_JARVIS_JOB_DIR = "/tmp/jarvis_konsole_jobs"
_KONSOLE_WAIT_TIMEOUT_S = 180.0


def _konsole_available():
    return shutil.which("konsole")


def _ensure_fifo():
    if os.path.exists(_JARVIS_FIFO):
        if os.path.isdir(_JARVIS_FIFO):
            return
        os.remove(_JARVIS_FIFO)
    os.mkfifo(_JARVIS_FIFO)


def _ensure_job_dir():
    os.makedirs(_JARVIS_JOB_DIR, exist_ok=True)


def _konsole_alive():
    global _KONSOLE_PROC
    return (
        _KONSOLE_PROC is not None
        and _KONSOLE_PROC.poll() is None
        and os.path.exists(_JARVIS_FIFO)
    )


def _start_konsole_runner(konsole_bin):
    global _KONSOLE_PROC
    _ensure_fifo()
    _ensure_job_dir()
    fifo_q = shlex.quote(_JARVIS_FIFO)
    job_dir_q = shlex.quote(_JARVIS_JOB_DIR)
    shell_bin = shutil.which("zsh") or "bash"
    shell_q = shlex.quote(shell_bin)
    runner = (
        f"FIFO={fifo_q}; JOB_DIR={job_dir_q}; SHELL_BIN={shell_q}; "
        'echo "[Jarvis Konsole] ready"; '
        'while true; do '
        'if IFS="|" read -r job_id job_b64 < "$FIFO"; then '
        'if [ -z "$job_id" ] || [ -z "$job_b64" ]; then continue; fi; '
        'out_file="$JOB_DIR/$job_id.out"; rc_file="$JOB_DIR/$job_id.rc"; '
        'cmd="$(printf %s "$job_b64" | base64 -d 2>/dev/null)"; '
        'printf "\\n%s\\n" "$cmd"; '
        '{ "$SHELL_BIN" -lc "$cmd"; printf "%s" "$?" > "$rc_file"; } 2>&1 | tee "$out_file"; '
        'printf "[Jarvis exit %s]\\n" "$(cat "$rc_file" 2>/dev/null || echo 1)"; '
        "fi; "
        "done"
    )
    _KONSOLE_PROC = subprocess.Popen(
        [konsole_bin, "--nofork", "--noclose", "-e", shell_bin, "-lc", runner]
    )


def _send_to_jarvis_konsole(job_id: str, cmd: str):
    encoded = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    payload = f"{job_id}|{encoded}\n".encode("utf-8")
    fd = os.open(_JARVIS_FIFO, os.O_WRONLY)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def _wait_for_job_result(job_id: str):
    out_path = os.path.join(_JARVIS_JOB_DIR, f"{job_id}.out")
    rc_path = os.path.join(_JARVIS_JOB_DIR, f"{job_id}.rc")
    start = time.time()
    while time.time() - start < _KONSOLE_WAIT_TIMEOUT_S:
        if os.path.exists(rc_path):
            break
        time.sleep(0.05)

    if not os.path.exists(rc_path):
        return {
            "status": "jarvis_konsole_timeout",
            "stdout": "",
            "stderr": "Timed out waiting for command completion in Jarvis Konsole.",
            "returncode": 124,
        }

    stdout = ""
    try:
        with open(out_path, "r", encoding="utf-8", errors="replace") as fh:
            stdout = fh.read()
    except OSError:
        stdout = ""

    try:
        with open(rc_path, "r", encoding="utf-8", errors="replace") as fh:
            rc = int((fh.read() or "1").strip())
    except Exception:
        rc = 1

    for p in (out_path, rc_path):
        try:
            os.remove(p)
        except OSError:
            pass

    return {
        "status": "executed_in_jarvis_konsole",
        "stdout": stdout,
        "stderr": "",
        "returncode": rc,
    }


def run_terminal(params):
    cmd = (params or {}).get("command", "")
    if not isinstance(cmd, str) or not cmd.strip():
        raise Exception("Missing terminal command")

    print(f"[Terminal] running: {cmd}")
    low = cmd.lower()
    if "rm " in low or low.startswith("rm") or "shutdown" in low:
        raise Exception("Blocked dangerous command")

    # Prefer one persistent visible Konsole session ("Jarvis Konsole").
    konsole = _konsole_available()
    if konsole:
        if not _konsole_alive():
            _start_konsole_runner(konsole)
        job_id = uuid.uuid4().hex
        try:
            _send_to_jarvis_konsole(job_id, cmd)
        except OSError:
            # Reader disappeared (user closed Konsole): reopen and retry once.
            _start_konsole_runner(konsole)
            _send_to_jarvis_konsole(job_id, cmd)
        result = _wait_for_job_result(job_id)
        result["command"] = cmd
        return result

    # Fallback: stream output live in current terminal while capturing it for the agent.
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    out_lines = []

    if proc.stdout is not None:
        for line in proc.stdout:
            out_lines.append(line)
            sys.stdout.write(line)
            sys.stdout.flush()

    rc = proc.wait()
    return {
        "stdout": "".join(out_lines),
        "stderr": "",
        "returncode": rc,
    }