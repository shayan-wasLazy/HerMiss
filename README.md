# HerMiss
**RL-Powered Autonomous PC Task Automation** — a local-first academic project combining deterministic task planning, sandboxed file operations, tabular Q-learning, independent verification, SQLite persistence, Streamlit, and FastAPI.

> This prototype supports explicit natural-language templates and simulation mode only. It is not an unrestricted LLM agent, and real desktop interaction is not enabled.

## Windows setup
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Run API: `uvicorn api:app --reload`  
Run tests: `python -m pytest -q`

## Supported examples
- `Create a folder called College`
- `find notes.txt`
- `rename notes.txt to summary.txt`
- `move assignment.pdf into College`

All file actions are constrained to `data/sandbox`. Existing files are not overwritten and path traversal is rejected. Training uses synthetic sandbox interactions; do not interpret its metrics as evidence of real-world desktop learning or superiority over a baseline.

## Architecture
```
app.py / api.py
agents/       Planner, action facade, verifier
automation/   Sandbox-safe filesystem
environment/  PC task environment and state encoder
rl/           Q-learning and training loop
storage/      SQLite Q-table and task history
evaluation/   Baseline, benchmark, metrics and plots
tests/        Unit and safety tests
```
