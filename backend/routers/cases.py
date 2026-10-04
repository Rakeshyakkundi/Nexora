import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.deps import get_current_user
from backend.models import Case, CaseCreateResponse, CaseDetailResponse, CaseSummary
from backend.store import create_case, delete_all_cases, delete_case, get_case, list_cases

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=list[CaseSummary])
async def list_cases_endpoint(current_user: str = Depends(get_current_user)):
    return list_cases()


@router.post("", response_model=CaseCreateResponse, status_code=201)
async def create_case_endpoint(
    title: str = Form(...),
    change_type: str = Form(...),
    description: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    current_user: str = Depends(get_current_user),
):
    filenames = [f.filename for f in files if f.filename]

    case = Case(
        id=str(uuid.uuid4()),
        title=title,
        change_type=change_type,
        description=description,
        filenames=filenames,
        status="submitted",
        created_at=datetime.now(timezone.utc),
        created_by=current_user,
    )
    create_case(case)

    return CaseCreateResponse(
        case_id=case.id,
        status=case.status,
        title=case.title,
        change_type=case.change_type,
        description=case.description,
        filenames=case.filenames,
        created_at=case.created_at,
        created_by=case.created_by,
    )


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case_endpoint(case_id: str, current_user: str = Depends(get_current_user)):
    case = get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return CaseDetailResponse(
        case_id=case.id,
        title=case.title,
        change_type=case.change_type,
        description=case.description,
        filenames=case.filenames,
        status=case.status,
        result=case.result,
        decision=case.decision,
        created_at=case.created_at,
        created_by=case.created_by,
        decided_by=case.decided_by,
        decided_at=case.decided_at,
    )


@router.delete("/{case_id}", status_code=204)
async def delete_case_endpoint(case_id: str, current_user: str = Depends(get_current_user)):
    if not delete_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")


@router.delete("")
async def delete_all_cases_endpoint(current_user: str = Depends(get_current_user)):
    deleted = delete_all_cases()
    return {"deleted": deleted}
