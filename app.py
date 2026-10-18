"""HerMiss Streamlit dashboard (simulation-only)."""
import tempfile,time
from pathlib import Path
import streamlit as st
from agents.planner import PlannerAgent,PlanningError
from agents.action_agent import ActionAgent
from config.settings import SANDBOX_DIR,DB_PATH,OUTPUT_DIR,RLConfig
from environment.pc_environment import PCEnvironment
from environment.sandbox import seed_sandbox
from rl.q_learning import QLearningAgent
from rl.trainer import train
from evaluation.plots import plot_training
from storage.database import RunStore
st.set_page_config(page_title="HerMiss",page_icon="🧠",layout="wide")
st.title("HerMiss")
st.caption("RL-Powered Autonomous PC Task Automation · Local simulation")
st.sidebar.info("Simulation only. Operations stay inside data/sandbox; desktop control is disabled.")
seed_sandbox(SANDBOX_DIR)
planner=PlannerAgent(); agent=QLearningAgent(learning_rate=RLConfig().learning_rate,discount_factor=RLConfig().discount_factor,epsilon_min=RLConfig().epsilon_min,epsilon_decay=RLConfig().epsilon_decay,db_path=DB_PATH)
store=RunStore(DB_PATH)
tab,training,history=st.tabs(["Task execution","RL training","History"])
with tab:
    goal=st.text_input("What should HerMiss do?",placeholder="Create a folder called College")
    if st.button("Run task",type="primary"):
        try:
            plan=planner.plan(goal); env=PCEnvironment(SANDBOX_DIR,max_steps=RLConfig().max_steps); env.reset(plan); total=0; logs=[]; start=time.perf_counter()
            for _ in range(env.max_steps):
                if env.done:break
                result=ActionAgent(agent).act(env)
                total+=result["reward"]; logs.append({"action":result["action"],"reward":result["reward"],"result":result["result"]["message"]})
            success=env.done and env.index>=len(plan.subtasks); elapsed=time.perf_counter()-start
            store.record_run(goal,"simulation",success,total,env.steps,elapsed)
            st.metric("Status","Verified success" if success else "Incomplete"); st.metric("Reward",f"{total:.1f}"); st.metric("Steps",env.steps); st.dataframe(logs,use_container_width=True)
            st.write("Plan:",[s.description for s in plan.subtasks])
            if env.errors:st.warning("; ".join(env.errors))
        except PlanningError as exc:st.error(str(exc))
with training:
    episodes=st.number_input("Training episodes",1,5000,100,25)
    if st.button("Start training"):
        with tempfile.TemporaryDirectory() as tmp:
            def factory(seed):
                root=Path(tmp)/str(seed); seed_sandbox(root); return PCEnvironment(root,max_steps=RLConfig().max_steps)
            results=train(agent,factory,int(episodes),RLConfig().seed)
        paths=plot_training(results,OUTPUT_DIR)
        st.metric("Measured success rate",f"{sum(r.success for r in results)/len(results):.1%}")
        st.metric("Mean episode reward",f"{sum(r.total_reward for r in results)/len(results):.2f}")
        st.dataframe([r.__dict__ for r in results]); 
        for p in paths:st.image(str(p))
with history:
    st.dataframe(store.runs(),use_container_width=True)
    st.caption(f"Persisted Q-table entries: {agent.q_value_count}")
