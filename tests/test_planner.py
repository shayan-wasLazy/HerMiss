from agents.planner import PlannerAgent, PlanningError


def test_create_folder():
    p = PlannerAgent().plan("Create a folder called College")
    assert p.subtasks[0].params["name"] == "College"


def test_move_dependencies():
    p = PlannerAgent().plan("move assignment.pdf into College")
    assert [s.action for s in p.subtasks] == ["CREATE_FOLDER", "MOVE_FILE"]


def test_project_scaffold_is_multi_step():
    p = PlannerAgent().plan("Set up a Python project called VisionAI")
    assert p.task_type == "project_scaffold"
    assert len(p.subtasks) >= 7
    assert p.subtasks[0].params["name"] == "VisionAI"
    assert p.subtasks[-1].params["name"] == "VisionAI/outputs"


def test_workspace_intelligence_tasks():
    planner = PlannerAgent()
    assert planner.plan("Organize my workspace by file type").subtasks[0].action == "ORGANIZE_BY_TYPE"
    assert planner.plan("Audit my workspace").subtasks[0].action == "AUDIT_WORKSPACE"


def test_reject_traversal():
    try:
        PlannerAgent().plan("create a folder called ../private")
    except PlanningError:
        return
    assert False
