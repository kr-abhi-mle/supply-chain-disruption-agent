"""Project tasks that work the same on Windows, macOS and Linux. Standard library only.

    python tasks.py              list the tasks (on Windows: py tasks.py)
    python tasks.py setup        install, create .env, build the index, check the key
    python tasks.py run "Heavy rains are delaying all freight leaving Sao Paulo for 5 days" --out results/sp

This script runs under any Python 3.8 or newer. It creates .venv with Python 3.11, using uv when it is
installed (uv downloads Python 3.11 if needed) and the standard venv and pip otherwise. Every step is
skipped when it is already done. The Makefile calls this script, so `make setup` does the same thing.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
INSTALLED = VENV / ".installed"   # marker: the packages match the current requirements.txt
REQUIREMENTS = ROOT / "requirements.txt"
DATA = ROOT / "data" / "processed" / "order_items.csv"
INDEX = ROOT / "data" / "chroma" / "chroma.sqlite3"
DEFAULT_QUERY = "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days"


def sh(*cmd, echo: bool = True) -> None:
    """Run a command in the project folder, showing it with paths relative to the project."""
    if echo:
        shown = [os.path.relpath(c, ROOT) if isinstance(c, Path) else str(c) for c in cmd]
        print("> " + (subprocess.list2cmdline(shown) if os.name == "nt" else shlex.join(shown)))
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def up_to_date(target: Path, source: Path) -> bool:
    return target.exists() and target.stat().st_mtime >= source.stat().st_mtime


def python311() -> Optional[List[str]]:
    """A command that starts Python 3.11 on this machine, or None."""
    candidates = [[sys.executable], ["python3.11"], ["py", "-3.11"]]
    for cmd in candidates:
        if shutil.which(cmd[0]) or Path(cmd[0]).exists():
            probe = subprocess.run(cmd + ["-c", "import sys; print(sys.version_info[:2] == (3, 11))"],
                                   capture_output=True, text=True)
            if probe.stdout.strip() == "True":
                return cmd
    return None


_checked = False   # install() runs once per command, however many tasks call it


def install(_args=None) -> None:
    """Create .venv with Python 3.11 and install the packages."""
    global _checked
    if _checked:
        return
    _checked = True
    uv = shutil.which("uv")
    if not PY.exists():
        if uv:
            sh(uv, "venv", "--python", "3.11", VENV)
        else:
            cmd = python311()
            if not cmd:
                sys.exit("Python 3.11 was not found. Install it from https://www.python.org/downloads/, "
                         "or install uv (https://docs.astral.sh/uv/), which downloads it for you.")
            sh(*cmd, "-m", "venv", VENV)
    if up_to_date(INSTALLED, REQUIREMENTS):
        print("Packages already installed.")
        return
    if uv:
        sh(uv, "pip", "install", "--python", PY, "-r", REQUIREMENTS)
    else:
        sh(PY, "-m", "pip", "install", "-r", REQUIREMENTS)
    INSTALLED.touch()


def env(_args=None) -> None:
    """Create .env from .env.example, if there is none yet."""
    if (ROOT / ".env").exists():
        print(".env already exists, left unchanged.")
    else:
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
        print("Created .env. Paste your Gemini key into it, or leave it to run offline.")


def index(_args=None) -> None:
    """Build the vector index (about 2 minutes, skipped when up to date)."""
    install()
    if up_to_date(INDEX, DATA):
        print("Index is up to date.")
    else:
        sh(PY, "-m", "src.build_index")


def check_key(_args=None) -> None:
    """Show whether runs will use Gemini or offline mode."""
    install()
    sh(PY, "-c", "from src import config; print('LLM mode:', config.LLM_MODE, '' if config.LLM_MODE == "
                 "'gemini' else '(add GEMINI_API_KEY to .env to use Gemini)')", echo=False)


def setup(_args=None) -> None:
    """Do everything: install, create .env, build the index, check the key."""
    install()
    env()
    index()
    check_key()


def run(args: List[str], offline: bool = False) -> None:
    """Run the CLI, with Gemini if a key is set. Usage: run "<query>" [--out DIR] [--emails N]."""
    install()
    if not args or args[0].startswith("-"):
        args = [DEFAULT_QUERY] + args
    sh(PY, "cli.py", *args, *(["--offline"] if offline else []))


def offline(args: List[str]) -> None:
    """Run the CLI offline. Usage: offline "<query>" [--out DIR]."""
    run(args, offline=True)


def app(_args=None) -> None:
    """Start the web app on http://localhost:8501."""
    install()
    sh(PY, "-m", "streamlit", "run", "app.py")


def test(args: List[str]) -> None:
    """Run the tests (no key needed). Extra arguments go to pytest."""
    install()
    sh(PY, "-m", "pytest", *args)


def docker(_args=None) -> None:
    """Build and start the app in Docker on http://localhost:8501."""
    compose = ["docker", "compose"]
    if subprocess.run(compose + ["version"], capture_output=True).returncode != 0:
        compose = ["docker-compose"]   # standalone Compose, e.g. Homebrew without the plugin set up
    sh(*compose, "up", "--build")


def clean(_args=None) -> None:
    """Remove .venv and the index. Keeps .env, data/processed and outputs."""
    for path in [VENV, ROOT / "data" / "chroma", ROOT / ".pytest_cache"]:
        remove(path)
    for path in ROOT.glob("**/__pycache__"):   # searched after .venv is gone, so this stays quick
        remove(path)
    print("Removed .venv and the index.")


def remove(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)
    if path.exists():
        print(f"Could not remove {path.relative_to(ROOT)}; close any program using it and retry.")


TASKS = {"setup": setup, "install": install, "env": env, "index": index, "check-key": check_key,
         "run": run, "offline": offline, "app": app, "test": test, "docker": docker, "clean": clean}


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)   # keep our lines in order with the commands' output
    name, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("help", [])
    if name not in TASKS:
        print(__doc__.split("\n\n")[0] + "\n\nTasks:")
        for task, func in TASKS.items():
            print(f"  {task:10} {func.__doc__.splitlines()[0]}")
        sys.exit(0 if name == "help" else 2)
    try:
        TASKS[name](args)
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
