"""Save training plots from actual episode measurements."""
def plot_training(results,output_dir):
    from pathlib import Path
    import matplotlib.pyplot as plt
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    paths=[]
    for field,title,name in [("total_reward","Episode reward","episode_reward.png"),("steps","Actions per episode","episode_steps.png")]:
        p=out/name; plt.figure(); plt.plot([getattr(r,field) for r in results]); plt.title(title); plt.xlabel("Episode"); plt.tight_layout(); plt.savefig(p); plt.close(); paths.append(p)
    return paths
