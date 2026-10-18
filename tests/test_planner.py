from agents.planner import PlannerAgent,PlanningError
def test_create_folder():
    p=PlannerAgent().plan("Create a folder called College")
    assert p.subtasks[0].params["name"]=="College"
def test_move_dependencies():
    p=PlannerAgent().plan("move assignment.pdf into College")
    assert [s.action for s in p.subtasks]==["CREATE_FOLDER","MOVE_FILE"]
def test_reject_traversal():
    try:PlannerAgent().plan("create a folder called ../private")
    except PlanningError:return
    assert False
