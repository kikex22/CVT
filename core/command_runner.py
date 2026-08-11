import os
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import TclError, messagebox


def _log_path(title):
    logs_dir = Path.home() / ".cache" / "cvt" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(
        char if char.isalnum() else "_"
        for char in title.lower()
    ).strip("_")
    safe_title = safe_title or "command"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return logs_dir / f"{stamp}_{safe_title}.log"


def _show_info(title, message):
    try:
        messagebox.showinfo(title, message)
    except TclError:
        print(f"{title}: {message}")


def _terminal_args(command, done_message):
    script = (
        f"{command}\n"
        "status=$?\n"
        "echo ''\n"
        f"echo {shlex.quote(done_message)}\n"
        "echo Exit code: $status\n"
        "exec bash\n"
    )

    candidates = [
        ("gnome-terminal", ["gnome-terminal", "--", "bash", "-lc", script]),
        ("x-terminal-emulator", ["x-terminal-emulator", "-e", "bash", "-lc", script]),
        ("konsole", ["konsole", "--noclose", "-e", "bash", "-lc", script]),
        ("xterm", ["xterm", "-hold", "-e", "bash", "-lc", script]),
    ]

    for binary, args in candidates:
        if shutil.which(binary):
            return args

    return None


def run_command(command, title, done_message):
    terminal_args = _terminal_args(command, done_message)
    if terminal_args:
        subprocess.Popen(terminal_args)
        return None

    log_path = _log_path(title)
    quoted_log = shlex.quote(str(log_path))
    logged_command = (
        "{ "
        f"echo {shlex.quote('$ ' + command)}; "
        "echo ''; "
        f"{command}; "
        "status=$?; "
        "echo ''; "
        f"echo {shlex.quote(done_message)}; "
        "echo Exit code: $status; "
        "exit $status; "
        f"}} > {quoted_log} 2>&1"
    )

    subprocess.Popen(
        ["bash", "-lc", logged_command],
        cwd=os.getcwd(),
        start_new_session=True,
    )

    _show_info(
        "Ejecutando",
        "No encontre una terminal grafica en este sistema.\n"
        "El comando se esta ejecutando en segundo plano.\n\n"
        f"Log:\n{log_path}"
    )
    return str(log_path)
