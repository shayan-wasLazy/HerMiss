"""HerMiss Streamlit dashboard with sandbox and restricted local-workspace modes."""
import json
import tempfile
import time
from pathlib import Path

import streamlit as st

from agents.planner import PlannerAgent, PlanningError
from agents.document_planner import build_document_plan, DocumentPlanningError
from agents.action_agent import ActionAgent
from automation.academic_organizer import build_organization_plan, apply_organization, extract_zip_safely
from config.settings import (
    SANDBOX_DIR, LOCAL_WORKSPACE_DIR, DB_PATH, OUTPUT_DIR, RLConfig
)
from environment.pc_environment import PCEnvironment
from environment.sandbox import seed_sandbox
from rl.q_learning import QLearningAgent
from rl.trainer import train
from evaluation.plots import plot_training
from storage.database import RunStore

st.set_page_config(page_title="HerMiss", page_icon="🧠", layout="wide")
st.title("HerMiss")
st.caption("RL-Powered Autonomous PC Task Automation · Local-first prototype")

with st.sidebar:
    st.header("Execution mode")
    mode = st.radio(
        "Where should file operations happen?",
        ["Desktop workspace", "Safe simulation"],
        index=0,
        help="Desktop workspace writes only inside the dedicated HerMissWorkspace folder. Simulation writes only inside data/sandbox.",
    )
    if mode == "Desktop workspace":
        active_root = LOCAL_WORKSPACE_DIR
        st.warning("Local file mode: changes are limited to the workspace shown below.")
        st.code(str(active_root), language=None)
        st.caption("This is a folder on the computer running this Python app. On Streamlit Cloud, that means the cloud server—not your personal PC.")
    else:
        active_root = SANDBOX_DIR
        st.info("Simulation mode: operations stay inside data/sandbox.")
        st.code(str(active_root), language=None)

# Seed only the synthetic sandbox. Never put fake sample files into the user's workspace.
seed_sandbox(SANDBOX_DIR)
active_root.mkdir(parents=True, exist_ok=True)

planner = PlannerAgent()
agent = QLearningAgent(
    learning_rate=RLConfig().learning_rate,
    discount_factor=RLConfig().discount_factor,
    epsilon_min=RLConfig().epsilon_min,
    epsilon_decay=RLConfig().epsilon_decay,
    db_path=DB_PATH,
)
store = RunStore(DB_PATH)

tab, document_planning, academic_organizer, training, history = st.tabs(["Task execution", "Plan from .txt", "Academic organizer", "RL training", "History"])
with tab:
    st.write("Try multi-step project scaffolding, type-based file organization, or a workspace audit. File actions remain restricted to the selected workspace; mouse, keyboard, and arbitrary application control are not enabled.")
    with st.expander("Example tasks to demonstrate"):
        st.code("Set up a Python project called VisionAI\\nOrganize my workspace by file type\\nAudit my workspace\\nCreate a folder called College", language=None)
    goal = st.text_input(
        "What should HerMiss do?",
        placeholder="Set up a Python project called VisionAI",
    )
    if st.button("Run task", type="primary"):
        try:
            plan = planner.plan(goal)
            env = PCEnvironment(active_root, max_steps=RLConfig().max_steps)
            env.reset(plan)
            total = 0.0
            logs = []
            start = time.perf_counter()
            for _ in range(env.max_steps):
                if env.done:
                    break
                result = ActionAgent(agent).act(env)
                total += result["reward"]
                logs.append({
                    "action": result["action"],
                    "reward": result["reward"],
                    "result": result["result"]["message"],
                })
            success = env.done and env.index >= len(plan.subtasks)
            elapsed = time.perf_counter() - start
            store.record_run(goal, "local_workspace" if mode == "Desktop workspace" else "simulation", success, total, env.steps, elapsed)
            st.metric("Status", "Verified success" if success else "Incomplete")
            st.metric("Reward", f"{total:.1f}")
            st.metric("Steps", env.steps)
            st.dataframe(logs, use_container_width=True)
            st.write("Plan:", [s.description for s in plan.subtasks])
            if success:
                st.success(f"Task completed. Workspace: {active_root}")
            if env.last_result is not None:
                st.subheader("Task output")
                st.json(env.last_result)
            if env.errors:
                st.warning("; ".join(env.errors))
        except PlanningError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Task failed safely: {exc}")

with document_planning:
    st.subheader("Turn a text file into a practical plan")
    st.write("Upload a syllabus/portion, assignment brief, or task list as a .txt file. HerMiss extracts topics and creates an ordered checklist with rough study-time estimates and session grouping. This creates a plan only; it does not execute the document's contents as PC actions.")
    uploaded = st.file_uploader("Choose a text file", type=["txt"], key="document_plan_upload")
    if uploaded is not None:
        try:
            document_text = uploaded.getvalue().decode("utf-8-sig")
            document_plan = build_document_plan(document_text, uploaded.name)
            st.success(f"Generated a plan from {document_plan['source_file']}")
            m1, m2, m3 = st.columns(3)
            m1.metric("Topics / tasks", document_plan["topic_count"])
            m2.metric("Estimated time", f"{document_plan['estimated_total_hours']} hours")
            m3.metric("Planned sessions", len(document_plan["sessions"]))
            st.subheader("Step-by-step plan")
            st.dataframe(document_plan["items"], use_container_width=True, hide_index=True)
            st.subheader("Suggested sessions")
            for session in document_plan["sessions"]:
                with st.expander(f"Session {session['session']} · {session['estimated_minutes']} min"):
                    for topic in session["topics"]:
                        st.markdown(f"- {topic}")
            st.info(document_plan["review"])
            st.caption(document_plan["note"])
            st.download_button(
                "Download plan as JSON",
                data=json.dumps(document_plan, indent=2, ensure_ascii=False),
                file_name=f"{Path(uploaded.name).stem}_plan.json",
                mime="application/json",
            )
        except UnicodeDecodeError:
            st.error("This file is not UTF-8 text. Save it as UTF-8 and upload it again.")
        except DocumentPlanningError as exc:
            st.error(str(exc))


with academic_organizer:
    st.subheader("Organize mixed college notes")
    st.write("Upload a ZIP or select a folder already inside the active workspace. HerMiss uses paths, filenames, and readable text snippets to estimate the subject and whether each file looks like theory, a lab, an assignment, a question paper, a presentation, or a project. Review the plan before copying files into the new structure.")
    source_kind = st.radio("Input source", ["Upload ZIP", "Folder inside active workspace"], horizontal=True, key="academic_source_kind")
    uploaded_zip = None
    source_relative = ""
    if source_kind == "Upload ZIP":
        uploaded_zip = st.file_uploader("Choose a ZIP of your notes", type=["zip"], key="academic_zip_upload")
    else:
        source_relative = st.text_input("Folder path relative to active workspace", placeholder="Mixed_Notes")
        st.caption(f"Source must be inside: {active_root}")
    if st.button("Preview organization plan", key="preview_academic_plan"):
        st.session_state.pop("academic_plan_rows", None)
        st.session_state.pop("academic_source_tmp", None)
        try:
            if source_kind == "Upload ZIP":
                if uploaded_zip is None:
                    st.error("Upload a ZIP first.")
                else:
                    temp_dir = tempfile.mkdtemp(prefix="hermiss_academic_")
                    zip_path = Path(temp_dir) / "input.zip"
                    zip_path.write_bytes(uploaded_zip.getvalue())
                    extracted = Path(temp_dir) / "extracted"
                    extract_zip_safely(zip_path, extracted)
                    st.session_state["academic_source_tmp"] = str(extracted)
                    rows = build_organization_plan(extracted)
                    st.session_state["academic_plan_rows"] = rows
                    st.session_state["academic_plan_source_kind"] = "zip"
                    st.session_state["academic_plan_temp_root"] = temp_dir
            else:
                if not source_relative.strip():
                    st.error("Enter a folder path relative to the active workspace.")
                    rows = None
                else:
                    source_root = (active_root / source_relative).resolve()
                    if active_root.resolve() not in source_root.parents or not source_root.is_dir():
                        st.error("That folder does not exist inside the active workspace.")
                        rows = None
                    else:
                        rows = build_organization_plan(source_root)
                        st.session_state["academic_source_tmp"] = str(source_root)
                        st.session_state["academic_plan_rows"] = rows
                        st.session_state["academic_plan_source_kind"] = "folder"
                        st.session_state["academic_plan_temp_root"] = ""
            if st.session_state.get("academic_plan_rows") is not None:
                st.success(f"Preview ready: {len(st.session_state['academic_plan_rows'])} file(s) classified.")
        except Exception as exc:
            st.error(f"Could not inspect this input safely: {exc}")
    rows = st.session_state.get("academic_plan_rows")
    if rows is not None:
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        needs_review = sum(bool(row["needs_review"]) for row in rows)
        st.metric("Files requiring manual review", needs_review)
        st.caption("Low-confidence files go to Needs_Review. The organizer copies files and never deletes the source. Subject/type detection is heuristic; PDF and Office document contents are not parsed in this first version, so filenames and folder names matter for those files.")
        if st.button("Copy files into organized structure", type="primary", key="apply_academic_plan"):
            try:
                source_root = Path(st.session_state["academic_source_tmp"])
                destination_root = active_root / "Organized_College_Notes"
                result = apply_organization(source_root, destination_root, rows)
                st.success(f"Copied {result['copied_count']} file(s) into {destination_root}")
                st.json({"copied_count": result["copied_count"], "skipped_count": result["skipped_count"], "destination": str(destination_root)})
                st.download_button("Download organization report", data=json.dumps(result, indent=2), file_name="hermiss_organization_report.json", mime="application/json")
            except Exception as exc:
                st.error(f"Organization stopped safely: {exc}")

with training:
    st.caption("Training episodes use temporary synthetic sandboxes, not your Desktop workspace.")
    episodes = st.number_input("Training episodes", 1, 5000, 100, 25)
    if st.button("Start training"):
        with tempfile.TemporaryDirectory() as tmp:
            def factory(seed):
                root = Path(tmp) / str(seed)
                seed_sandbox(root)
                return PCEnvironment(root, max_steps=RLConfig().max_steps)
            results = train(agent, factory, int(episodes), RLConfig().seed)
        paths = plot_training(results, OUTPUT_DIR)
        st.metric("Measured success rate", f"{sum(r.success for r in results) / len(results):.1%}")
        st.metric("Mean episode reward", f"{sum(r.total_reward for r in results) / len(results):.2f}")
        st.dataframe([r.__dict__ for r in results])
        for path in paths:
            st.image(str(path))

with history:
    st.dataframe(store.runs(), use_container_width=True)
    st.caption(f"Persisted Q-table entries: {agent.q_value_count}")
