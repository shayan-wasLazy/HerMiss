"""Deterministic sandbox environment with reset() and step()."""
from pathlib import Path
from agents.planner import TaskPlan,Subtask
from automation.filesystem import SandboxFilesystem
from config.settings import RewardConfig
class PCEnvironment:
    def __init__(self,root:Path,rewards:RewardConfig|None=None,max_steps:int=20):
        self.fs=SandboxFilesystem(root); self.rewards=rewards or RewardConfig(); self.max_steps=max_steps
        self.plan=None; self.index=0; self.steps=0; self.done=False; self.last_success=True; self.last_action=""; self.errors=[]
    def reset(self,plan:TaskPlan|None=None):
        self.plan=plan or TaskPlan("create a folder called College","create_folder",[Subtask("CREATE_FOLDER",{"name":"College"})])
        self.index=self.steps=0; self.done=False; self.last_success=True; self.last_action=""; self.errors=[]
        return self.observe()
    def observe(self):
        sub=self.plan.subtasks[self.index] if self.plan and self.index<len(self.plan.subtasks) else None
        target=(sub.params.get("name") or sub.params.get("source") or "") if sub else ""
        exists=bool(target and "/" not in target and "\\" not in target and self.fs.resolve(target).exists())
        return {"task_type":self.plan.task_type if self.plan else "unknown","subtask_index":self.index,"progress":self.index/max(1,len(self.plan.subtasks)) if self.plan else 0,"last_action_success":self.last_success,"target_exists":exists,"remaining_steps":max(0,self.max_steps-self.steps),"stage":"complete" if self.done else (sub.action.lower() if sub else "finish"),"current_subtask":sub.description if sub else "Finished","last_action":self.last_action,"errors":list(self.errors),"files":self.fs.list_directory()}
    def valid_actions(self):
        if self.done:return ["FINISH"]
        sub=self.plan.subtasks[self.index] if self.plan and self.index<len(self.plan.subtasks) else None
        if not sub:return ["FINISH"]
        return {"CREATE_FOLDER":["CREATE_FOLDER","INSPECT","RETRY"],"FIND_FILE":["FIND_FILE","INSPECT","RETRY"],"RENAME_FILE":["RENAME_FILE","INSPECT","RETRY"],"MOVE_FILE":["MOVE_FILE","INSPECT","RETRY"],"OPEN_FILE":["OPEN_FILE","INSPECT","RETRY"]}.get(sub.action,["INSPECT","RETRY"])+["FINISH"]
    def step(self,action):
        if self.done:return self.observe(),0.0,True,{"success":True,"message":"Episode already complete."}
        self.steps+=1; reward=self.rewards.step_cost; success=False; message=""; sub=self.plan.subtasks[self.index] if self.index<len(self.plan.subtasks) else None
        try:
            if self.steps>self.max_steps: raise ValueError("Step budget exceeded.")
            if action not in self.valid_actions(): raise ValueError(f"Invalid action {action}.")
            if action=="FINISH":
                if sub: raise ValueError("Cannot finish before planned subtasks are verified.")
                self.done=True; success=True; message="Task complete."
            elif action=="INSPECT": success=True; message="Sandbox inspected."
            elif action=="RETRY": reward+=self.rewards.unnecessary_action; message="Retry requested."
            else:
                p=sub.params
                if action=="CREATE_FOLDER":
                    changed=self.fs.create_folder(p["name"]); success=True; message="Folder created." if changed else "Folder already exists and was verified."
                elif action=="FIND_FILE":
                    found=self.fs.find_file(p["name"]); success=found is not None; message=f"Found {found.relative_to(self.fs.root)}" if found else f"Missing {p['name']}"
                elif action=="RENAME_FILE": self.fs.rename_file(p["source"],p["destination"]); success=True; message="File renamed."
                elif action=="MOVE_FILE": self.fs.move_file(p["source"],p["destination"]); success=True; message="File moved."
                elif action=="OPEN_FILE": success=self.fs.find_file(p["name"]) is not None; message="File exists; desktop opening is disabled in simulation."
                if success:
                    self.index+=1; reward+=self.rewards.useful_subtask
                    if self.index>=len(self.plan.subtasks): self.done=True; reward+=self.rewards.task_complete
                else: reward+=self.rewards.action_failure
        except Exception as exc:
            self.errors.append(str(exc)); message=str(exc); reward+=self.rewards.invalid_action if isinstance(exc,ValueError) else self.rewards.action_failure
        self.last_success=success; self.last_action=action
        return self.observe(),reward,self.done,{"success":success,"message":message,"action":action}
