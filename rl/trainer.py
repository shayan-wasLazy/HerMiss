"""Repeatable Q-learning episodes on simulated tasks."""
from dataclasses import dataclass
from agents.planner import TaskPlan,Subtask
from environment.state_encoder import encode_state
@dataclass
class EpisodeResult:
    episode:int
    total_reward:float
    steps:int
    success:bool
def train(agent,env_factory,episodes=100,seed=42):
    results=[]
    for ep in range(episodes):
        env=env_factory(seed+ep); env.reset(TaskPlan("create folder College","create_folder",[Subtask("CREATE_FOLDER",{"name":"College"})]))
        total=0
        for _ in range(env.max_steps):
            s=encode_state(env.observe()); a=agent.select_action(s,env.valid_actions(),explore=True)
            obs,r,done,info=env.step(a); total+=r
            agent.update(s,a,r,encode_state(obs),env.valid_actions(),terminal=done)
            if done:break
        agent.decay_epsilon(); results.append(EpisodeResult(ep+1,total,env.steps,env.done))
    return results
