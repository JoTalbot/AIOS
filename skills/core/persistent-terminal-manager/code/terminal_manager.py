#!/usr/bin/env python3
"""Bounded persistent terminal manager (PTY) for Octopus."""

from __future__ import annotations

import os
import pty
import select
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

MAX_SESSIONS = int(os.environ.get("PTM_MAX_SESSIONS", "8"))
MAX_OUTPUT_LINES = int(os.environ.get("PTM_MAX_OUTPUT_LINES", "2000"))
DEFAULT_WAIT_IDLE_MS = int(os.environ.get("PTM_WAIT_IDLE_MS", "1500"))
DEFAULT_TIMEOUT_S = int(os.environ.get("PTM_DEFAULT_TIMEOUT_S", "300"))


class Session:
    def __init__(self, session_id: str, cmd: List[str], cwd: Optional[str] = None):
        self.id = session_id
        self.cmd = cmd
        self.cwd = cwd or os.getcwd()
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.buffer: deque = deque(maxlen=MAX_OUTPUT_LINES)
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: Optional[str] = None
        self.returncode: Optional[int] = None
        self._lock = threading.RLock()
        self._stop = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cmd": self.cmd,
            "cwd": self.cwd,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "returncode": self.returncode,
            "buffer_lines": len(self.buffer),
        }


class TerminalManager:
    def __init__(self) -> None:
        self.sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        self._counter = 0

    def _next_id(self) -> str:
        with self._lock:
            self._counter += 1
            return "ptm-" + str(int(time.time() * 1000)) + "-" + str(self._counter).zfill(4)

    def create(self, cmd: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if len(self.sessions) >= MAX_SESSIONS:
                return {"ok": False, "error": "max_sessions_reached: " + str(MAX_SESSIONS)}
            session_id = self._next_id()
            session = Session(session_id, cmd, cwd)
            self.sessions[session_id] = session
        return {"ok": True, "session": session.to_dict()}

    def start(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "session_not_found"}
        if session.master_fd is not None:
            return {"ok": False, "error": "already_started"}

        try:
            master_fd, slave_fd = pty.openpty()
        except OSError as exc:
            return {"ok": False, "error": "pty_open_failed: " + str(exc)}

        try:
            proc = subprocess.Popen(
                session.cmd,
                cwd=session.cwd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
            session.master_fd = master_fd
            session.slave_fd = slave_fd
            session.pid = proc.pid
        except Exception as exc:
            try:
                os.close(master_fd)
                os.close(slave_fd)
            except OSError:
                pass
            session.master_fd = None
            session.slave_fd = None
            return {"ok": False, "error": "spawn_failed: " + str(exc)}

        t = threading.Thread(target=self._reader, args=(session, proc), daemon=True)
        t.start()
        return {"ok": True, "session": session.to_dict()}

    def _reader(self, session: Session, proc: subprocess.Popen) -> None:
        try:
            while not session._stop and proc.poll() is None:
                r, _, _ = select.select([session.master_fd], [], [], 0.05)
                if session.master_fd in r:
                    try:
                        data = os.read(session.master_fd, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")
                    with session._lock:
                        for line in text.splitlines():
                            session.buffer.append(line)
            proc.wait()
            session.returncode = proc.returncode
        except Exception:
            session.returncode = -1
        finally:
            try:
                os.close(session.master_fd)
                if session.slave_fd is not None:
                    os.close(session.slave_fd)
            except OSError:
                pass
            session.finished_at = datetime.now(timezone.utc).isoformat()

    def wait_idle(self, session_id: str, idle_ms: int = DEFAULT_WAIT_IDLE_MS) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session or session.master_fd is None:
            return {"ok": False, "error": "session_not_found_or_not_started"}
        start = time.time()
        last_len = len(session.buffer)
        while True:
            time.sleep(0.1)
            with session._lock:
                cur_len = len(session.buffer)
            if cur_len != last_len:
                last_len = cur_len
                start = time.time()
            if time.time() - start >= idle_ms / 1000:
                break
            if session.finished_at is not None:
                break
            if time.time() - time.fromisoformat(session.started_at).timestamp() >= DEFAULT_TIMEOUT_S:
                break
        return {"ok": True, "session": session.to_dict()}

    def stop(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "session_not_found"}
        session._stop = True
        if session.pid is not None:
            try:
                os.kill(session.pid, 9)
            except ProcessLookupError:
                pass
        with self._lock:
            self.sessions.pop(session_id, None)
        return {"ok": True, "session": session.to_dict()}

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.sessions.values()]

    def get_output(self, session_id: str, tail: int = 200) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"ok": False, "error": "session_not_found"}
        with session._lock:
            lines = list(session.buffer)[-tail:]
        return {"ok": True, "session": session.to_dict(), "tail": tail, "lines": lines}


manager = TerminalManager()


def run(cmd: str = "") -> Dict[str, Any]:
    return {
        "skill": "persistent-terminal-manager",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "manager": manager.list_sessions(),
        "limits": {
            "max_sessions": MAX_SESSIONS,
            "max_output_lines": MAX_OUTPUT_LINES,
            "default_wait_idle_ms": DEFAULT_WAIT_IDLE_MS,
            "default_timeout_s": DEFAULT_TIMEOUT_S,
        },
    }


if __name__ == "__main__":
    import sys, json
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    payload: Dict[str, Any]
    if action == "list":
        payload = run()
    elif action == "create" and len(sys.argv) > 2:
        payload = manager.create(sys.argv[2:])
    elif action == "start" and len(sys.argv) > 2:
        payload = manager.start(sys.argv[2])
    elif action == "stop" and len(sys.argv) > 2:
        payload = manager.stop(sys.argv[2])
    elif action == "output" and len(sys.argv) > 2:
        payload = manager.get_output(sys.argv[2])
    else:
        payload = {"ok": False, "error": "usage: run.py [list|create cmd [args]|start id|stop id|output id]"}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
