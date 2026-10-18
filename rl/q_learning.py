"""Tabular Q-learning with optional SQLite persistence."""
import random,sqlite3
from collections import defaultdict
from pathlib import Path
class QLearningAgent:
    def __init__(self,learning_rate=.15,discount_factor=.9,epsilon=1.0,epsilon_min=.05,epsilon_decay=.985,seed=42,db_path=None):
        self.alpha=learning_rate; self.gamma=discount_factor; self.epsilon=epsilon; self.epsilon_min=epsilon_min; self.epsilon_decay=epsilon_decay
        self.random=random.Random(seed); self.q=defaultdict(dict); self.db_path=Path(db_path) if db_path else None
        if self.db_path:self.db_path.parent.mkdir(parents=True,exist_ok=True); self._init_db(); self._load()
    def _connect(self): return sqlite3.connect(self.db_path)
    def _init_db(self):
        with self._connect() as c:c.execute("CREATE TABLE IF NOT EXISTS q_values(state TEXT, action TEXT, value REAL, PRIMARY KEY(state,action))")
    def _load(self):
        with self._connect() as c:
            for s,a,v in c.execute("SELECT state,action,value FROM q_values"):self.q[s][a]=v
    @property
    def q_value_count(self):return sum(len(v) for v in self.q.values())
    def select_action(self,state,valid_actions,explore=False):
        actions=list(valid_actions)
        if not actions:raise ValueError("No valid actions.")
        if explore and self.random.random()<self.epsilon:return self.random.choice(actions)
        return max(actions,key=lambda a:self.q[state].get(a,0.0))
    def update(self,state,action,reward,next_state,next_actions,terminal=False):
        old=self.q[state].get(action,0.0); future=0.0 if terminal or not next_actions else max(self.q[next_state].get(a,0.0) for a in next_actions)
        value=old+self.alpha*(reward+self.gamma*future-old); self.q[state][action]=value
        if self.db_path:
            with self._connect() as c:c.execute("INSERT INTO q_values VALUES(?,?,?) ON CONFLICT(state,action) DO UPDATE SET value=excluded.value",(state,action,value))
        return value
    def decay_epsilon(self):self.epsilon=max(self.epsilon_min,self.epsilon*self.epsilon_decay)
