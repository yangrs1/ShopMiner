"""Playwright Web 测试 conftest - 独立进程Flask服务器"""
import os
import socket
import subprocess
import sys
import time
import pytest


HOST = "127.0.0.1"
PORT = 5000


def _wait_port(host, port, timeout=30):
    for i in range(timeout * 2):
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def _free_port():
    try:
        import signal
        if sys.platform == "win32":
            out = subprocess.check_output(
                f'netstat -ano | findstr ":{PORT} " | findstr LISTEN',
                shell=True, timeout=5
            ).decode()
            for line in out.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, timeout=5)
        else:
            subprocess.run(f"fuser -k {PORT}/tcp", shell=True, timeout=5)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def flask_server():
    _free_port()

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(project_root, "test_web.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    server_script = os.path.join(os.path.dirname(__file__), "server.py")
    env = os.environ.copy()
    env["FLASK_ENV"] = "testing"
    env["WEB_TEST_DB"] = db_path
    env["FLASK_LIMITER_ENABLED"] = "false"

    proc = subprocess.Popen(
        [sys.executable, server_script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if not _wait_port(HOST, PORT):
        proc.kill()
        raise RuntimeError(f"Flask server failed to start on {HOST}:{PORT}")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait()

    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
