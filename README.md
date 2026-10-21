# HerMiss
**RL-Powered Autonomous PC Task Automation** — a local-first academic prototype combining template-based planning, workspace-constrained filesystem operations, tabular Q-learning, SQLite persistence, Streamlit, and FastAPI.

> This is a bounded prototype, not an unrestricted LLM or desktop-control agent. It does not control the mouse, keyboard, browser, or arbitrary applications.

## Windows setup

Open PowerShell in the repository folder:

```powershell
py -3.11 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Run tests with:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Advanced demo tasks

Enter these in the task box:

1. **Multi-step project scaffolding**
   `Set up a Python project called VisionAI`

   Creates a nested structure with `src`, `tests`, `data/raw`, `data/processed`, `docs`, and `outputs`. The dashboard logs each planned action and reward.

2. **Workspace file organization**
   `Organize my workspace by file type`

   Sorts top-level files into `Images`, `Documents`, `Code`, `Archives`, `Audio`, `Video`, or `Other`. Existing destination files are not overwritten; collisions are reported.

3. **Workspace audit**
   `Audit my workspace`

   Reports file/folder counts, total file size, extension distribution, and groups of files with identical SHA-256 content. This is read-only.

4. **Basic task**
   `Create a folder called College`

## Plan from a text file

Open the **Plan from .txt** tab and upload a UTF-8 `.txt` file such as `portion.txt`. It extracts bullet points, numbered entries, headings/lines, and comma- or semicolon-separated topics, then builds an ordered checklist, rough per-topic time estimates, session groupings, and a downloadable JSON plan. This is a deterministic heuristic planner: review its extracted topics and estimates before relying on it. It generates a plan; it does not execute arbitrary instructions found in uploaded files.

## Local workspace and safety

The app's **Desktop workspace** mode uses a dedicated `HerMissWorkspace` folder on the Desktop by default. The displayed workspace path is the boundary for all filesystem operations. You can override it in `.env`:

```dotenv
HERMISS_WORKSPACE=C:/Users/YourName/Desktop/HerMissWorkspace
```

The separate **Safe simulation** mode uses `data/sandbox`. Organization changes files inside the selected workspace, so test with copies of files first. Path traversal is blocked and existing files are not overwritten.

If deployed to Streamlit Cloud, the workspace belongs to the cloud server. Run the app locally to operate on your own PC.

## RL caveat and evaluation

The project uses tabular Q-learning with discrete states, valid-action filtering, reward feedback, and persisted Q-values. The natural-language planner is template-based. The training loop currently uses a narrow synthetic folder-creation task; the advanced task demonstrations exercise additional environment actions but are not themselves evidence that a policy has learned superior general behavior. A rigorous evaluation should compare trained and untrained policies on the same held-out tasks and report success rate, cumulative reward, and steps to completion.

## Architecture

```
app.py / api.py
agents/       Planner, action facade, verifier
automation/   Workspace-constrained filesystem and audit tools
environment/  PC task environment, state encoder, discrete actions
rl/           Q-learning and training loop
storage/      SQLite Q-table and task history
evaluation/   Baseline, benchmark, metrics and plots
tests/        Unit and safety tests
```

## Academic notes organizer

Open the **Academic organizer** tab to upload a mixed-notes ZIP or select an existing folder inside the active workspace. Preview the proposed subject and document-type labels before applying. The organizer copies files into `Organized_College_Notes/<Subject>/<Type>/`, and sends low-confidence files to `Needs_Review/`. Existing source files are not deleted and name collisions receive a suffix rather than being overwritten. ZIP extraction rejects path traversal and symbolic-link entries.

This first version is deliberately heuristic: it looks at folder paths, filenames, and snippets from supported plain-text formats. It does not yet semantically read PDF or Office document contents, so descriptive filenames/folder names improve classification. Verify the preview and manually review uncertain files before relying on the output. Use **Safe simulation** to test first.

## Dashboard modules

The Streamlit UI now includes:
- **Overview:** saved task counts, task success rate, current workspace file count, duplicate groups, and recent task activity.
- **Task automation:** existing template-based planner and restricted filesystem task execution.
- **Smart file manager:** the academic organizer supports ZIP uploads or folders inside the active workspace, previews heuristic classifications, copies organized files, and exports a mapping report.
- **RL training studio:** trains the current tabular Q-learning agent on a synthetic folder-creation task and plots measured episode metrics.
- **Performance analytics:** charts recorded task rewards, success/failure counts, execution time, steps, and current-session training summaries.
- **Safety & audit:** requires explicit confirmation before a read-only workspace audit; shows extension counts and duplicate SHA-256 groups.
- **Workflow builder:** preview and export predefined workflow plans as JSON. It is a plan visualizer, not a free-form drag-and-drop editor and does not execute workflows itself.
- **Experiment comparison:** compares RL training summaries created during the current Streamlit browser session. This is not yet a cross-algorithm benchmark.
- **Export reports:** download task history as CSV/JSON, training summaries as JSON, and the latest audit as JSON.
- **History:** displays persisted task runs and Q-table entry count.

### Dashboard interpretation and limitations

Dashboard metrics reflect recorded runs and workspace contents. Training summaries are held in Streamlit session state and may reset when the session ends. The existing trainer currently learns on a narrow synthetic folder-creation task; these dashboard additions do not change that training environment or establish general desktop automation. The app does not currently offer pause/resume for running tasks or automatic rollback. Use a copy of important files and verify output reports before relying on file organization.
