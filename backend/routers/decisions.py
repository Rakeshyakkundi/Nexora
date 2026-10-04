from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.deps import get_current_user
from backend.models import DecisionRequest, DecisionResponse
from backend.store import get_case, save_case

router = APIRouter(prefix="/api/cases", tags=["decisions"])


@router.post("/{case_id}/decision", response_model=DecisionResponse)
async def post_decision_endpoint(
    case_id: str, body: DecisionRequest, current_user: str = Depends(get_current_user)
):
    case = get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.status != "complete":
        raise HTTPException(status_code=409, detail="Case assessment is not complete yet")

    case.decision = body.decision
    case.decided_by = current_user
    case.decided_at = datetime.now(timezone.utc)
    save_case(case)

    return DecisionResponse(
        case_id=case.id,
        decision=case.decision,
        decided_by=case.decided_by,
        decided_at=case.decided_at,
    )
