from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from backend.agents.master_agent import run_pipeline
from backend.deps import get_current_user
from backend.models import RunResponse
from backend.store import get_case, save_case

router = APIRouter(prefix="/api/cases", tags=["agents"])


@router.post("/{case_id}/run", response_model=RunResponse)
async def run_agents_endpoint(case_id: str, current_user: str = Depends(get_current_user)):
    case = get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = "running"
    save_case(case)

    agent_results, result = await run_in_threadpool(run_pipeline, case)

    case.agent_results = {a.agent: a for a in agent_results}
    case.result = result
    case.status = "complete"
    save_case(case)

    return RunResponse(case_id=case.id, status=case.status, agents=agent_results)


@router.get("/{case_id}/agents", response_model=RunResponse)
async def get_agents_endpoint(case_id: str, current_user: str = Depends(get_current_user)):
    case = get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return RunResponse(
        case_id=case.id,
        status=case.status,
        agents=list(case.agent_results.values()),
    )
