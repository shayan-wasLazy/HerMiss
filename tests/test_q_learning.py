from rl.q_learning import QLearningAgent
def test_terminal_no_bootstrap():
    a=QLearningAgent(learning_rate=1,discount_factor=.9,epsilon=0)
    a.q["next"]["A"]=100
    assert a.update("s","A",5,"next",["A"],terminal=True)==5
def test_persistence(tmp_path):
    p=tmp_path/"q.sqlite3"; a=QLearningAgent(learning_rate=1,db_path=p);a.update("s","A",7,"n",[],terminal=True)
    assert QLearningAgent(db_path=p).q["s"]["A"]==7
