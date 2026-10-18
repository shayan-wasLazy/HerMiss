"""Compute metrics from real episode records."""
def summarize(results):
    if not results:return {"episodes":0,"success_rate":0.0,"mean_reward":0.0,"mean_steps":0.0}
    n=len(results)
    return {"episodes":n,"success_rate":sum(bool(x.success) for x in results)/n,"mean_reward":sum(x.total_reward for x in results)/n,"mean_steps":sum(x.steps for x in results)/n}
