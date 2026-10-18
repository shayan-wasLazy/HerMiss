"""SQLite storage for task run history."""
import sqlite3
from pathlib import Path
class RunStore:
    def __init__(self,path:Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as c:c.execute("CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, goal TEXT, mode TEXT, success INTEGER, reward REAL, steps INTEGER, elapsed REAL)")
    def _connect(self):return sqlite3.connect(self.path)
    def record_run(self,goal,mode,success,reward,steps,elapsed):
        with self._connect() as c:c.execute("INSERT INTO runs(goal,mode,success,reward,steps,elapsed) VALUES(?,?,?,?,?,?)",(goal,mode,int(success),reward,steps,elapsed))
    def runs(self):
        with self._connect() as c:return c.execute("SELECT id,goal,mode,success,reward,steps,elapsed FROM runs ORDER BY id DESC").fetchall()
