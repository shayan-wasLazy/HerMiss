"""Fixed-rule baseline for comparison."""
def choose_baseline_action(env):
    actions=env.valid_actions()
    sub=env.plan.subtasks[env.index] if env.plan and env.index<len(env.plan.subtasks) else None
    return sub.action if sub and sub.action in actions else ("FINISH" if "FINISH" in actions else actions[0])
