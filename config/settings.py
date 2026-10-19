"""Central settings for HerMiss."""
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _default_desktop() -> Path:
    """Resolve a common Windows Desktop location, including OneDrive redirection."""
    home = Path.home()
    one_drive = os.environ.get("OneDrive")
    candidates = [
        home / "Desktop",
        home / "OneDrive" / "Desktop",
    ]
    if one_drive:
        candidates.insert(0, Path(one_drive) / "Desktop")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return home / "Desktop"


@dataclass(frozen=True)
class RLConfig:
    learning_rate: float = 0.15
    discount_factor: float = 0.9
    epsilon_start: float = 1.0
    epsilon_min: float = 0.05
    epsilon_decay: float = 0.985
    max_steps: int = 20
    seed: int = 42


@dataclass(frozen=True)
class RewardConfig:
    task_complete: float = 100.0
    useful_subtask: float = 10.0
    action_failure: float = -10.0
    unnecessary_action: float = -2.0
    invalid_action: float = -20.0
    step_cost: float = -1.0


SANDBOX_DIR = Path(os.getenv("HERMISS_SANDBOX") or (ROOT / "data" / "sandbox")).expanduser().resolve()
DB_PATH = Path(os.getenv("HERMISS_DB") or (ROOT / "data" / "hermiss.sqlite3")).expanduser().resolve()
OUTPUT_DIR = Path(os.getenv("HERMISS_OUTPUT") or (ROOT / "outputs")).expanduser().resolve()
LOCAL_WORKSPACE_DIR = Path(
    os.getenv("HERMISS_WORKSPACE") or (_default_desktop() / "HerMissWorkspace")
).expanduser().resolve()
