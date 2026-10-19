"""Template-based natural-language planner; unsupported tasks are rejected."""
from dataclasses import dataclass, field
import re


@dataclass
class Subtask:
    action: str
    params: dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class TaskPlan:
    goal: str
    task_type: str
    subtasks: list[Subtask]


class PlanningError(ValueError):
    pass


class PlannerAgent:
    def plan(self, goal: str) -> TaskPlan:
        t = goal.strip()
        if not t:
            raise PlanningError("Please enter a task.")

        # Impressive multi-step task: scaffold a standard Python project.
        m = re.search(r'(?:set up|scaffold|initialize|init) (?:a )?(?:python )?project (?:called|named) ["\']?([\w .-]+)', t, re.I)
        if m:
            name = m.group(1).strip().rstrip(".")
            self._safe(name)
            paths = [
                name, f"{name}/src", f"{name}/tests", f"{name}/data",
                f"{name}/data/raw", f"{name}/data/processed",
                f"{name}/docs", f"{name}/outputs",
            ]
            return TaskPlan(t, "project_scaffold", [
                Subtask("CREATE_FOLDER", {"name": path}, f"Create {path}") for path in paths
            ])

        if re.search(r'\borganize (?:my )?(?:workspace|files|folder) by (?:file )?type\b', t, re.I):
            return TaskPlan(t, "organize_by_type", [
                Subtask("ORGANIZE_BY_TYPE", {}, "Sort workspace files into type-based folders")
            ])

        if re.search(r'\b(?:audit|analyze|analyse|inspect) (?:my )?(?:workspace|folder|files)\b', t, re.I):
            return TaskPlan(t, "workspace_audit", [
                Subtask("AUDIT_WORKSPACE", {}, "Count files, measure storage, and detect duplicate content")
            ])

        m = re.search(r'(?:create|make) (?:a )?(?:new )?folder (?:called|named) ["\']?([\w .-]+)', t, re.I)
        if m:
            name = m.group(1).strip().rstrip(".")
            self._safe(name)
            return TaskPlan(t, "create_folder", [Subtask("CREATE_FOLDER", {"name": name}, f"Create folder {name}")])

        m = re.search(r'rename ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})["\']? to ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})', t, re.I)
        if m:
            a, b = map(str.strip, m.groups())
            self._safe(a); self._safe(b)
            return TaskPlan(t, "rename_file", [Subtask("RENAME_FILE", {"source": a, "destination": b}, f"Rename {a} to {b}")])

        m = re.search(r'(?:move|put|organize) ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})["\']? (?:into|to|in) (?:my )?(?:folder )?["\']?([\w .-]+)', t, re.I)
        if m:
            src, folder = map(str.strip, m.groups())
            folder = folder.rstrip(".")
            self._safe(src); self._safe(folder)
            return TaskPlan(t, "move_file", [
                Subtask("CREATE_FOLDER", {"name": folder}, f"Ensure {folder} exists"),
                Subtask("MOVE_FILE", {"source": src, "destination": folder}, f"Move {src} into {folder}"),
            ])

        m = re.search(r'(?:find|locate|look for) ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})', t, re.I)
        if m:
            n = m.group(1).strip(); self._safe(n)
            return TaskPlan(t, "find_file", [Subtask("FIND_FILE", {"name": n}, f"Find {n}")])

        m = re.search(r'open ["\']?([\w .-]+\.[A-Za-z0-9]{1,8})', t, re.I)
        if m:
            n = m.group(1).strip(); self._safe(n)
            return TaskPlan(t, "open_file", [Subtask("OPEN_FILE", {"name": n}, f"Verify file {n} exists")])

        raise PlanningError("Unsupported task. Try scaffolding a Python project, organizing files by type, auditing the workspace, creating a folder, finding, renaming, or moving a file.")

    @staticmethod
    def _safe(name):
        if not name or name in {".", ".."} or any(c in name for c in ("/", "\\", ":")) or ".." in name:
            raise PlanningError(f"Unsafe name: {name!r}")
