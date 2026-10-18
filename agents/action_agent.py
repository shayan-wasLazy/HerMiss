"""Execute the action selected by the learned policy."""
from environment.state_encoder import encode_state
class ActionAgent:
    def __init__(self,policy):self.policy=policy
    def act(self,env,explore=False):
        state=encode_state(env.observe()); action=self.policy.select_action(state,env.valid_actions(),explore)
        obs,reward,done,info=env.step(action)
        self.policy.update(state,action,reward,encode_state(obs),env.valid_actions(),terminal=done)
        return {"observation":obs,"action":action,"reward":reward,"done":done,"result":info}
