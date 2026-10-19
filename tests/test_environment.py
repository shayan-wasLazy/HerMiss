from agents.planner import TaskPlan, Subtask, PlannerAgent
from environment.pc_environment import PCEnvironment


def test_create_folder(tmp_path):
    env = PCEnvironment(tmp_path)
    env.reset(TaskPlan("create", "create_folder", [Subtask("CREATE_FOLDER", {"name": "College"})]))
    _, reward, done, info = env.step("CREATE_FOLDER")
    assert done and (tmp_path / "College").is_dir() and info["success"] and reward > 0


def test_invalid_action(tmp_path):
    env = PCEnvironment(tmp_path)
    env.reset()
    _, reward, _, info = env.step("OPEN_APPLICATION")
    assert not info["success"] and reward < 0


def test_project_scaffold_creates_nested_structure(tmp_path):
    plan = PlannerAgent().plan("Set up a Python project called VisionAI")
    env = PCEnvironment(tmp_path, max_steps=30)
    env.reset(plan)
    for _ in range(env.max_steps):
        if env.done:
            break
        _, _, _, info = env.step(plan.subtasks[env.index].action)
        assert info["success"], info["message"]
    assert env.done
    assert (tmp_path / "VisionAI" / "src").is_dir()
    assert (tmp_path / "VisionAI" / "data" / "raw").is_dir()
    assert (tmp_path / "VisionAI" / "tests").is_dir()


def test_organize_by_type(tmp_path):
    (tmp_path / "photo.png").write_bytes(b"image")
    (tmp_path / "notes.txt").write_text("hello")
    env = PCEnvironment(tmp_path)
    env.reset(PlannerAgent().plan("Organize my workspace by file type"))
    _, _, done, info = env.step("ORGANIZE_BY_TYPE")
    assert done and info["success"]
    assert (tmp_path / "Images" / "photo.png").is_file()
    assert (tmp_path / "Documents" / "notes.txt").is_file()


def test_audit_detects_duplicate_content(tmp_path):
    (tmp_path / "a.txt").write_text("same")
    (tmp_path / "b.txt").write_text("same")
    env = PCEnvironment(tmp_path)
    env.reset(PlannerAgent().plan("Audit my workspace"))
    _, _, done, info = env.step("AUDIT_WORKSPACE")
    assert done and info["success"]
    assert info["result"]["file_count"] == 2
    assert len(info["result"]["duplicate_groups"]) == 1
