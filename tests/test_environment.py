from agents.planner import TaskPlan,Subtask
from environment.pc_environment import PCEnvironment
def test_create_folder(tmp_path):
    env=PCEnvironment(tmp_path);env.reset(TaskPlan("create","create_folder",[Subtask("CREATE_FOLDER",{"name":"College"})]))
    _,reward,done,info=env.step("CREATE_FOLDER")
    assert done and (tmp_path/"College").is_dir() and info["success"] and reward>0
def test_invalid_action(tmp_path):
    env=PCEnvironment(tmp_path);env.reset()
    _,reward,_,info=env.step("OPEN_APPLICATION")
    assert not info["success"] and reward<0
