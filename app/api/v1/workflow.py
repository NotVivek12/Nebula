import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.models.workflow import Workflow, WorkflowNodeLog, WorkflowRun
from app.schemas.workflow import (
    WorkflowApproveRequest,
    WorkflowCreate,
    WorkflowNodeLogResponse,
    WorkflowResponse,
    WorkflowRunResponse,
)
from app.services.workflow.engine import WorkflowEngine

router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    membership: BusinessUser = Depends(RequirePermission("workflows:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Creates a new automation workflow definition (requires workflows:write permission)."""
    workflow = Workflow(
        name=payload.name,
        trigger_type=payload.trigger_type,
        definition=payload.definition,
        is_active=payload.is_active,
        business_id=membership.business_id,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_workflow_run(
    workflow_id: uuid.UUID,
    initial_variables: dict[str, Any],
    membership: BusinessUser = Depends(RequirePermission("workflows:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Manually triggers execution of a business workflow run (requires workflows:write permission)."""
    engine = WorkflowEngine()
    try:
        run_id = await engine.trigger_workflow(
            workflow_id=workflow_id,
            initial_variables=initial_variables,
            db=db,
        )
        # Fetch the created run metadata
        run = await db.get(WorkflowRun, run_id)
        return run
    except ValueError as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{workflow_id}/run", response_model=list[WorkflowRunResponse])
async def list_workflow_runs(
    workflow_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    membership: BusinessUser = Depends(RequirePermission("workflows:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieves execution run histories of a specific workflow definition (requires workflows:read)."""
    # Verify workflow ownership
    workflow = await db.get(Workflow, workflow_id)
    if not workflow or workflow.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found within this business tenant.",
        )

    query = (
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id)
        .order_by(WorkflowRun.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/run/{run_id}/logs", response_model=list[WorkflowNodeLogResponse])
async def get_run_logs(
    run_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("workflows:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieves chronological execution step logs for a run instance (requires workflows:read)."""
    # Verify run ownership
    query = (
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.workflow))
    )
    res = await db.execute(query)
    run = res.scalar_one_or_none()

    if not run or run.workflow.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run execution not found within this business tenant.",
        )

    log_query = (
        select(WorkflowNodeLog)
        .where(WorkflowNodeLog.run_id == run_id)
        .order_by(WorkflowNodeLog.created_at.asc())
    )
    res = await db.execute(log_query)
    return res.scalars().all()


@router.post("/run/{run_id}/approve")
async def approve_workflow_run(
    run_id: uuid.UUID,
    payload: WorkflowApproveRequest,
    membership: BusinessUser = Depends(RequirePermission("workflows:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Manually approves or denies a paused Human Approval node run (requires workflows:write)."""
    # Verify run ownership
    query = (
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.workflow))
    )
    res = await db.execute(query)
    run = res.scalar_one_or_none()

    if not run or run.workflow.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run execution not found within this business tenant.",
        )

    engine = WorkflowEngine()
    try:
        await engine.resume_run(
            run_id=run_id,
            action_data={"decision": payload.decision, "notes": payload.notes},
            db=db,
        )
        return {"status": "resumed", "run_id": str(run_id)}
    except ValueError as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
