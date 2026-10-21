"""HerMiss Streamlit dashboard with sandbox and restricted local-workspace modes."""
import csv
import io
import json
import tempfile
import time
from pathlib import Path

import streamlit as st

from agents.planner import PlannerAgent, PlanningError
from agents.document_planner import build_document_plan, DocumentPlanningError
from agents.adaptive_quiz import AdaptiveQuizPolicy, QuizGenerationError, generate_mcqs
from agents.action_agent import ActionAgent
from automation.academic_organizer import build_organization_plan, apply_organization, extract_zip_safely
from automation.filesystem import SandboxFilesystem
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

overview, tab, document_planning, adaptive_quiz, academic_organizer, training, analytics, safety_audit, workflow_builder, experiment_comparison, reports, history = st.tabs(["Overview", "Task automation", "Plan from .txt", "Adaptive quiz", "Smart file manager", "RL training studio", "Performance analytics", "Safety & audit", "Workflow builder", "Experiment comparison", "Export reports", "History"])
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


with adaptive_quiz:
    st.subheader("Adaptive MCQ practice from your notes")
    st.write("Upload readable .txt notes. HerMiss builds fill-the-term MCQs from statements in the text, then uses a small Q-learning policy to prioritize weak or slow questions based on your attempts. It does not currently read PDF/Word files or generate expert-level semantic questions.")
    quiz_policy = AdaptiveQuizPolicy(DB_PATH.with_name("quiz_progress.json"))
    quiz_upload = st.file_uploader("Upload notes (.txt)", type=["txt"], key="adaptive_quiz_upload")
    quiz_count = st.slider("Questions to generate", min_value=5, max_value=30, value=10, step=5, key="adaptive_quiz_count")
    if st.button("Generate quiz from notes", type="primary", key="generate_adaptive_quiz"):
        try:
            if quiz_upload is None:
                st.error("Upload a .txt file first.")
            else:
                source_text = quiz_upload.getvalue().decode("utf-8-sig")
                generated = generate_mcqs(source_text, quiz_count, quiz_upload.name)
                st.session_state["adaptive_quiz_questions"] = generated
                st.session_state["adaptive_quiz_source"] = quiz_upload.name
                st.session_state["adaptive_quiz_index"] = 0
                st.session_state["adaptive_quiz_answers"] = {}
                st.session_state["adaptive_quiz_feedback"] = None
                st.session_state["adaptive_quiz_current_id"] = None
                st.session_state["adaptive_quiz_submitted"] = False
                st.session_state["adaptive_quiz_started_at"] = time.perf_counter()
                st.success(f"Generated {len(generated)} MCQs from {quiz_upload.name}. Review the source statement shown with each question.")
        except UnicodeDecodeError:
            st.error("This file is not UTF-8 text. Save it as UTF-8 and upload it again.")
        except QuizGenerationError as exc:
            st.error(str(exc))
    questions = st.session_state.get("adaptive_quiz_questions", [])
    if questions:
        index = st.session_state.get("adaptive_quiz_index", 0)
        if index < len(questions):
            strategy = quiz_policy.choose_strategy()
            answered_ids = set(st.session_state.get("adaptive_quiz_answers", {}).keys())
            remaining_questions = [q for q in questions if q["id"] not in answered_ids]
            ordered = quiz_policy.prioritize(remaining_questions or questions, strategy)
            # Keep the active question stable; only choose the next unanswered item using the adaptive policy.
            current_id = st.session_state.get("adaptive_quiz_current_id")
            if current_id not in {q["id"] for q in questions}:
                current_id = None
            if current_id is None:
                current = ordered[0]
                st.session_state["adaptive_quiz_current_id"] = current["id"]
                st.session_state["adaptive_quiz_started_at"] = time.perf_counter()
            else:
                current = next((q for q in questions if q["id"] == current_id), ordered[0])
            st.progress(min(1.0, (index + 1) / len(questions)), text=f"Question {index + 1} of {len(questions)}")
            st.markdown(current["question"])
            st.caption(f"Source file: {current['source_name']} · Generated from a statement in the uploaded notes")
            answer = st.radio("Choose one answer", current["options"], key=f"adaptive_answer_{current['id']}", index=None)
            if st.button("Submit answer", key=f"submit_{current['id']}"):
                if answer is None:
                    st.warning("Choose an option before submitting.")
                else:
                    elapsed = max(0.0, time.perf_counter() - st.session_state.get("adaptive_quiz_started_at", time.perf_counter()))
                    is_correct = answer.casefold() == current["answer"].casefold()
                    result = quiz_policy.record_answer(current["id"], is_correct, elapsed)
                    st.session_state["adaptive_quiz_feedback"] = {
                        "question_id": current["id"], "correct": is_correct, "answer": current["answer"],
                        "selected": answer, "elapsed": round(elapsed, 1), "reward": result["reward"],
                        "wrong": result["wrong"], "slow": result["slow"], "strategy": result["strategy"],
                    }
                    st.session_state["adaptive_quiz_answers"][current["id"]] = is_correct
                    st.session_state["adaptive_quiz_submitted"] = True
            feedback = st.session_state.get("adaptive_quiz_feedback")
            if feedback and feedback.get("question_id") == current["id"] and st.session_state.get("adaptive_quiz_submitted"):
                if feedback["correct"]:
                    st.success(f"Correct · {feedback['elapsed']}s · RL reward {feedback['reward']:+.2f}")
                else:
                    st.error(f"Not quite. The notes-based answer is: {feedback['answer']}")
                st.write("Source statement:", current["source_sentence"])
                stats = quiz_policy.stats.get(current["id"], {})
                if stats.get("wrong", 0) >= 2:
                    st.warning("This question has been missed repeatedly. The practice policy will prioritize it for targeted review.")
                elif stats.get("slow", 0) >= 1:
                    st.info("This question has taken over 20 seconds before. The policy will schedule more review.")
                if st.button("Next question", key=f"next_{current['id']}"):
                    st.session_state["adaptive_quiz_index"] = index + 1
                    st.session_state["adaptive_quiz_current_id"] = None
                    st.session_state["adaptive_quiz_submitted"] = False
                    st.session_state["adaptive_quiz_feedback"] = None
                    st.session_state["adaptive_quiz_started_at"] = time.perf_counter()
                    st.rerun()
        else:
            summary = quiz_policy.summary()
            st.success("Practice set complete.")
            m1, m2, m3 = st.columns(3)
            m1.metric("Set accuracy", f"{sum(st.session_state.get('adaptive_quiz_answers', {}).values()) / max(1, len(st.session_state.get('adaptive_quiz_answers', {}))):.0%}")
            m2.metric("Questions tracked", summary["questions_tracked"])
            m3.metric("Repeatedly missed", summary["repeatedly_missed"])
            st.write("Adaptive policy summary")
            st.json(summary)
            st.caption("Progress and Q-values persist in the local data folder. This is a small tabular Q-learning practice-prioritization prototype, not a validated cognitive model.")
            if st.button("Restart this quiz", key="restart_adaptive_quiz"):
                st.session_state["adaptive_quiz_index"] = 0
                st.session_state["adaptive_quiz_answers"] = {}
                st.session_state["adaptive_quiz_feedback"] = None
                st.session_state["adaptive_quiz_current_id"] = None
                st.session_state["adaptive_quiz_submitted"] = False
                st.session_state["adaptive_quiz_started_at"] = time.perf_counter()
                st.rerun()

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
        summary = {"run_id": len(st.session_state.get("rl_experiment_runs", [])) + 1, "episodes": int(episodes), "success_rate": sum(r.success for r in results) / max(1, len(results)), "mean_reward": sum(r.total_reward for r in results) / max(1, len(results)), "mean_steps": sum(r.steps for r in results) / max(1, len(results)), "q_values_after": agent.q_value_count}
        st.session_state.setdefault("rl_experiment_runs", []).append(summary)
        st.metric("Measured success rate", f"{sum(r.success for r in results) / len(results):.1%}")
        st.metric("Mean episode reward", f"{sum(r.total_reward for r in results) / len(results):.2f}")
        st.dataframe([r.__dict__ for r in results])
        for path in paths:
            st.image(str(path))

with overview:
    runs = store.runs()
    total_runs = len(runs)
    successes = sum(1 for row in runs if row[3])
    try:
        audit_snapshot = SandboxFilesystem(active_root).audit_workspace()
    except Exception as exc:
        audit_snapshot = {"file_count": 0, "folder_count": 0, "total_bytes": 0, "duplicate_groups": []}
        st.warning(f"Workspace summary unavailable: {exc}")
    cols = st.columns(4)
    cols[0].metric("Tasks recorded", total_runs)
    cols[1].metric("Task success rate", f"{successes / total_runs * 100:.1f}%" if total_runs else "—")
    cols[2].metric("Files in workspace", audit_snapshot["file_count"])
    cols[3].metric("Duplicate groups", len(audit_snapshot["duplicate_groups"]))
    st.subheader("Recent task activity")
    if runs:
        st.dataframe([{"Run": r[0], "Task": r[1], "Mode": r[2], "Success": bool(r[3]), "Reward": r[4], "Steps": r[5], "Seconds": round(r[6], 2)} for r in runs[:8]], use_container_width=True, hide_index=True)
    else:
        st.info("No tasks recorded yet. Run a task from Task automation to populate this dashboard.")
    st.subheader("Current workspace")
    st.code(str(active_root), language=None)
    st.caption("Overview uses saved task history and a read-only filesystem audit; it does not predict agent capability.")

with analytics:
    st.subheader("Performance analytics")
    runs = store.runs()
    if not runs:
        st.info("Run a task first. Charts will use saved execution history.")
    else:
        rows = [{"run_id": r[0], "success": int(r[3]), "reward": float(r[4]), "steps": int(r[5]), "seconds": float(r[6]), "mode": r[2], "goal": r[1]} for r in reversed(runs)]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.line_chart([{"run_id": r["run_id"], "reward": r["reward"]} for r in rows], x="run_id", y="reward")
        st.bar_chart([{"result": "Success", "count": sum(r["success"] for r in rows)}, {"result": "Failure", "count": len(rows) - sum(r["success"] for r in rows)}], x="result", y="count")
        st.metric("Mean steps", f"{sum(r['steps'] for r in rows) / len(rows):.2f}")
        st.metric("Mean execution time", f"{sum(r['seconds'] for r in rows) / len(rows):.2f} s")
    training_runs = st.session_state.get("rl_experiment_runs", [])
    if training_runs:
        st.subheader("RL training run metrics")
        st.dataframe(training_runs, use_container_width=True, hide_index=True)
        st.line_chart([{"run_id": r["run_id"], "mean_reward": r["mean_reward"]} for r in training_runs], x="run_id", y="mean_reward")

with safety_audit:
    st.subheader("Safety and audit center")
    st.warning("Auditing is read-only. Organizing and copying files require explicit actions in their respective tabs.")
    st.write("Execution mode:", mode)
    st.code(str(active_root), language=None)
    confirmed = st.checkbox("I understand this scan reads metadata and hashes file contents; it will not modify files.", key="confirm_workspace_audit")
    if st.button("Run read-only workspace audit", disabled=not confirmed):
        try:
            st.session_state["latest_workspace_audit"] = SandboxFilesystem(active_root).audit_workspace()
            st.session_state["latest_workspace_audit_root"] = str(active_root)
        except Exception as exc:
            st.error(f"Audit failed: {exc}")
    audit = st.session_state.get("latest_workspace_audit")
    if audit:
        st.caption(f"Last audited workspace: {st.session_state.get('latest_workspace_audit_root', 'unknown')}")
        cols = st.columns(4)
        cols[0].metric("Files", audit["file_count"])
        cols[1].metric("Folders", audit["folder_count"])
        cols[2].metric("Total size", f"{audit['total_bytes'] / (1024 * 1024):.2f} MB")
        cols[3].metric("Duplicate groups", len(audit["duplicate_groups"]))
        st.dataframe([{"Extension": k, "Count": v} for k, v in audit["extensions"].items()], use_container_width=True, hide_index=True)
        if audit["duplicate_groups"]:
            st.dataframe([{"Group": i + 1, "Files": " · ".join(group)} for i, group in enumerate(audit["duplicate_groups"])], use_container_width=True, hide_index=True)
        else:
            st.success("No duplicate-content groups found.")
        st.download_button("Export audit as JSON", data=json.dumps(audit, indent=2), file_name="hermiss_workspace_audit.json", mime="application/json")
    st.caption("This prototype does not provide general desktop control or automatic rollback. Keep backups before organizing important files.")

with workflow_builder:
    st.subheader("Visual workflow builder")
    templates = {
        "Organize academic notes": [("Inspect archive", "Read paths and supported text snippets", "Read-only"), ("Classify files", "Estimate subject, category and confidence", "Heuristic"), ("Review uncertain files", "Send low-confidence items to Needs_Review", "Human review"), ("Preview destinations", "Show proposed folder tree", "Preview"), ("Copy organized files", "Copy without deleting source files", "Explicit action"), ("Export report", "Save source-to-destination mapping", "Export")],
        "Audit workspace": [("Enumerate files", "Count files and folders", "Read-only"), ("Calculate hashes", "Group identical file contents by SHA-256", "Read-only"), ("Summarize extensions", "Count file types and total size", "Read-only"), ("Export audit", "Download audit results as JSON", "Export")],
        "Create project scaffold": [("Parse request", "Extract requested project name", "Planning"), ("Validate paths", "Reject unsafe path components", "Safety check"), ("Create directories", "Create the planned project tree", "Write"), ("Verify result", "Check created directories and report status", "Verification")],
    }
    chosen_flow = st.selectbox("Workflow template", list(templates))
    flow = templates[chosen_flow]
    st.caption("This is a visual plan preview; it does not run actions by itself.")
    for i, (name, detail, stage) in enumerate(flow, 1):
        with st.container(border=True):
            st.markdown(f"**{i}. {name}**")
            st.write(detail)
            st.caption(f"Stage: {stage}")
            if i < len(flow): st.markdown("↓")
    workflow_json = {"workflow": chosen_flow, "steps": [{"order": i, "name": x[0], "description": x[1], "stage": x[2]} for i, x in enumerate(flow, 1)]}
    st.download_button("Export workflow definition (JSON)", data=json.dumps(workflow_json, indent=2), file_name="hermiss_workflow.json", mime="application/json")

with experiment_comparison:
    st.subheader("Experiment comparison")
    st.write("Compare recorded training runs. The current training loop uses the existing tabular Q-learning agent on a narrow synthetic folder-creation task; these metrics are not evidence of general PC automation.")
    experiment_runs = st.session_state.get("rl_experiment_runs", [])
    if experiment_runs:
        st.dataframe(experiment_runs, use_container_width=True, hide_index=True)
        st.bar_chart([{"Run": f"Run {r['run_id']}", "Mean reward": r["mean_reward"]} for r in experiment_runs], x="Run", y="Mean reward")
        st.bar_chart([{"Run": f"Run {r['run_id']}", "Success rate (%)": r["success_rate"] * 100} for r in experiment_runs], x="Run", y="Success rate (%)")
        st.download_button("Export experiment comparison", data=json.dumps(experiment_runs, indent=2), file_name="hermiss_rl_experiment_comparison.json", mime="application/json")
    else:
        st.info("Start a run in RL training studio. Repeated runs can be compared in this browser session.")

with reports:
    st.subheader("Exportable reports")
    runs = store.runs()
    run_dicts = [{"id": r[0], "goal": r[1], "mode": r[2], "success": bool(r[3]), "reward": r[4], "steps": r[5], "elapsed_seconds": r[6]} for r in runs]
    st.write("Download task history, RL training summaries, or the most recent workspace audit.")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "goal", "mode", "success", "reward", "steps", "elapsed_seconds"])
    writer.writeheader(); writer.writerows(run_dicts)
    st.download_button("Download task history (CSV)", data=buffer.getvalue(), file_name="hermiss_task_history.csv", mime="text/csv", disabled=not run_dicts)
    st.download_button("Download task history (JSON)", data=json.dumps(run_dicts, indent=2), file_name="hermiss_task_history.json", mime="application/json", disabled=not run_dicts)
    training_runs = st.session_state.get("rl_experiment_runs", [])
    st.download_button("Download RL training summaries (JSON)", data=json.dumps(training_runs, indent=2), file_name="hermiss_training_summaries.json", mime="application/json", disabled=not training_runs)
    latest_audit = st.session_state.get("latest_workspace_audit")
    st.download_button("Download latest audit (JSON)", data=json.dumps(latest_audit, indent=2) if latest_audit else "{}", file_name="hermiss_latest_audit.json", mime="application/json", disabled=not latest_audit)

with history:
    st.dataframe(store.runs(), use_container_width=True)
    st.caption(f"Persisted Q-table entries: {agent.q_value_count}")
