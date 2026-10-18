"""Stable discrete state encoder for tabular Q-learning."""
import json
def encode_state(observation:dict)->str:
    keys=("task_type","subtask_index","progress","last_action_success","target_exists","remaining_steps","stage","last_action")
    return json.dumps({k:observation.get(k) for k in keys},sort_keys=True,separators=(",",":"))
