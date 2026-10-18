"""Template-based natural-language planner; unsupported tasks are rejected."""
from dataclasses import dataclass,field
import re
@dataclass
class Subtask:
    action:str
    params:dict[str,str]=field(default_factory=dict)
    description:str=""
@dataclass
class TaskPlan:
    goal:str
    task_type:str
    subtasks:list[Subtask]
class PlanningError(ValueError): pass
class PlannerAgent:
    def plan(self,goal:str)->TaskPlan:
        t=goal.strip()
        if not t: raise PlanningError("Please enter a task.")
        patterns=[
          (r'(?:create|make) (?:a )?(?:new )?folder (?:called|named) ["\']?([\w .-]+)',"create_folder"),
        ]
        m=re.search(patterns[0][0],t,re.I)
        if m:
            name=m.group(1).strip().rstrip("."); self._safe(name)
            return TaskPlan(t,"create_folder",[Subtask("CREATE_FOLDER",{"name":name},f"Create folder {name}")])
        m=re.search(r'rename ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})["\']? to ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})',t,re.I)
        if m:
            a,b=map(str.strip,m.groups()); self._safe(a); self._safe(b)
            return TaskPlan(t,"rename_file",[Subtask("RENAME_FILE",{"source":a,"destination":b},f"Rename {a} to {b}")])
        m=re.search(r'(?:move|put|organize) ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})["\']? (?:into|to|in) (?:my )?(?:folder )?["\']?([\w .-]+)',t,re.I)
        if m:
            src,folder=map(str.strip,m.groups()); folder=folder.rstrip("."); self._safe(src); self._safe(folder)
            return TaskPlan(t,"move_file",[Subtask("CREATE_FOLDER",{"name":folder},f"Ensure {folder} exists"),Subtask("MOVE_FILE",{"source":src,"destination":folder},f"Move {src} into {folder}")])
        m=re.search(r'(?:find|locate|look for) ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})',t,re.I)
        if m:
            n=m.group(1).strip(); self._safe(n)
            return TaskPlan(t,"find_file",[Subtask("FIND_FILE",{"name":n},f"Find {n}")])
        m=re.search(r'open ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})',t,re.I)
        if m:
            n=m.group(1).strip(); self._safe(n)
            return TaskPlan(t,"open_file",[Subtask("OPEN_FILE",{"name":n},f"Verify file {n} exists")])
        raise PlanningError("Unsupported task. Try creating a folder, finding a file, renaming a file, or moving a file into a folder.")
    @staticmethod
    def _safe(name):
        if not name or name in {".",".."} or any(c in name for c in ("/","\\",":")) or ".." in name:
            raise PlanningError(f"Unsafe name: {name!r}")
