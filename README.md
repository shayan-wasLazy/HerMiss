# HerMiss
**RL-Powered Autonomous PC Task Automation** — a local-first academic prototype combining template-based task planning, sandboxed filesystem operations, tabular Q-learning, SQLite persistence, Streamlit, and FastAPI.

> This prototype supports a small set of explicit natural-language task templates. It is not an unrestricted LLM agent and does not control the mouse, keyboard, browser, or arbitrary applications.

## Windows setup

Open PowerShell in the repository folder. These commands avoid the PowerShell virtual-environment activation-policy issue:

```powershell
py -3.11 -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed in the terminal, usually `http://localhost:8501`.

Run tests:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run API:
```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --reload
```

## Local folder creation

The app starts in **Desktop workspace** mode. By default, folder operations are restricted to a dedicated `HerMissWorkspace` folder on your Desktop. For example, asking `Create a folder called College` creates:

```
Desktop/
└── HerMissWorkspace/
    └── College/
```

The workspace path is shown in the app sidebar. The app can use an existing Desktop location including a common OneDrive Desktop location. To choose another workspace, set `HERMISS_WORKSPACE` in your local `.env` file to an absolute path, for example:

```dotenv
HERMISS_WORKSPACE=C:/Users/YourName/Desktop/HerMissWorkspace
```

**Safety boundary:** all filesystem actions are constrained to the selected workspace. HerMiss will not create folders directly anywhere on your PC, overwrite existing files, or permit path traversal. Put files you want to organize inside the workspace first. The separate **Safe simulation** mode uses only `data/sandbox`.

**Important:** this is a local app. If deployed to Streamlit Cloud, its “Desktop workspace” is on the cloud server, not on your personal computer. Run the app using the commands above on the PC where you want the folder created.

## Supported examples

- `Create a folder called College`
- `find notes.txt`
- `rename notes.txt to summary.txt`
- `move assignment.pdf into College`

Training uses synthetic sandbox interactions. Do not interpret its metrics as evidence of real-world desktop learning or superiority over a baseline.

## Architecture

```
app.py / api.py
agents/       Planner, action facade, verifier
automation/   Workspace-constrained filesystem
environment/  PC task environment and state encoder
rl/           Q-learning and training loop
storage/      SQLite Q-table and task history
evaluation/   Baseline, benchmark, metrics and plots
tests/        Unit and safety tests
```
