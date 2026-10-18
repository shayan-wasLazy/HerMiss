"""FastAPI endpoints for planning and health checks."""
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from agents.planner import PlannerAgent,PlanningError
app=FastAPI(title="HerMiss API",version="0.1.0")
class PlanRequest(BaseModel):goal:str
@app.get("/health")
def health():return {"status":"ok","mode":"simulation"}
@app.post("/plan")
def make_plan(request:PlanRequest):
    try:
        p=PlannerAgent().plan(request.goal)
        return {"goal":p.goal,"task_type":p.task_type,"subtasks":[{"action":s.action,"params":s.params,"description":s.description} for s in p.subtasks]}
    except PlanningError as exc:raise HTTPException(status_code=422,detail=str(exc))
