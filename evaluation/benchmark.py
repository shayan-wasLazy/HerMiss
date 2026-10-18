"""Small deterministic benchmark task set."""
from agents.planner import TaskPlan,Subtask
def benchmark_tasks():
    return [
      TaskPlan("create folder College","create_folder",[Subtask("CREATE_FOLDER",{"name":"College"})]),
      TaskPlan("find notes.txt","find_file",[Subtask("FIND_FILE",{"name":"notes.txt"})]),
      TaskPlan("move assignment.pdf into College","move_file",[Subtask("CREATE_FOLDER",{"name":"College"}),Subtask("MOVE_FILE",{"source":"assignment.pdf","destination":"College"})]),
    ]
