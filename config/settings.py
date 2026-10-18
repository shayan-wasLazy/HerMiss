"""Central settings for HerMiss."""
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@dataclass(frozen=True)
class RLConfig:
    learning_rate:float=0.15
    discount_factor:float=0.9
    epsilon_start:float=1.0
    epsilon_min:float=0.05
    epsilon_decay:float=0.985
    max_steps:int=20
    seed:int=42
@dataclass(frozen=True)
class RewardConfig:
    task_complete:float=100.0
    useful_subtask:float=10.0
    action_failure:float=-10.0
    unnecessary_action:float=-2.0
    invalid_action:float=-20.0
    step_cost:float=-1.0
SANDBOX_DIR=ROOT/"data"/"sandbox"
DB_PATH=ROOT/"data"/"hermiss.sqlite3"
OUTPUT_DIR=ROOT/"outputs"
