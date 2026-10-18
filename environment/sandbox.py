"""Seed repeatable sample files into a sandbox."""
from pathlib import Path
def seed_sandbox(root:Path)->Path:
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    for name,content in {"notes.txt":"HerMiss sample notes\n","assignment.pdf":"SIMULATED PDF CONTENT\n"}.items():
        p=root/name
        if not p.exists(): p.write_text(content,encoding="utf-8")
    return root
