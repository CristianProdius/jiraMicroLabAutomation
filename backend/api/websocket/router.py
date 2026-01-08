"""WebSocket API routes."""

import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from api.db.database import SessionLocal
from api.auth.models import User
from api.auth.security import decode_token
from api.websocket.manager import manager
from api.websocket.events import WebSocketEvent, EventType

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def get_user_from_token(token: str) -> Optional[User]:
    """Validate JWT token and get user."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    # sub is stored as string in JWT, convert to int
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    finally:
        db.close()


@router.websocket("/analysis/{job_id}")
async def websocket_job_updates(
    websocket: WebSocket,
    job_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for subscribing to a specific job's updates.

    Connect: ws://host/api/v1/ws/analysis/{job_id}?token=<jwt_token>

    Events received:
    - JOB_STARTED: When job begins processing
    - JOB_PROGRESS: Progress updates during analysis
    - ISSUE_STARTED: When analysis of an issue begins
    - ISSUE_RUBRIC_COMPLETE: Rubric evaluation completed
    - ISSUE_COMPLETE: Full analysis completed for an issue
    - ISSUE_FAILED: If analysis of an issue fails
    - JOB_COMPLETED: When job finishes successfully
    - JOB_FAILED: If job fails
    """
    # Authenticate
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify job belongs to user
    db = SessionLocal()
    try:
        from api.feedback.models import AnalysisJob

        job = db.query(AnalysisJob).filter(
            AnalysisJob.job_id == job_id,
            AnalysisJob.user_id == user.id,
        ).first()

        if not job:
            await websocket.close(code=4004, reason="Job not found")
            return
    finally:
        db.close()

    # Connect and handle messages
    await manager.connect(websocket, user.id, job_id)

    try:
        while True:
            # Receive messages (for ping/pong or future commands)
            data = await websocket.receive_text()

            # Handle ping
            if data == "ping":
                await manager.send_personal(
                    websocket,
                    WebSocketEvent.create(EventType.PONG, message="pong"),
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.websocket("/live")
async def websocket_live_feed(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for receiving all user activity updates.

    Connect: ws://host/api/v1/ws/live?token=<jwt_token>

    Events received:
    - ACTIVITY: General activity events
    - JOB_STARTED/PROGRESS/COMPLETED: All job updates
    - ISSUE_* events: All issue analysis events

    This is useful for the dashboard's live activity feed.
    """
    # Authenticate
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Connect without job_id to receive all user events
    await manager.connect(websocket, user.id, job_id=None)

    try:
        while True:
            data = await websocket.receive_text()

            # Handle ping
            if data == "ping":
                await manager.send_personal(
                    websocket,
                    WebSocketEvent.create(EventType.PONG, message="pong"),
                )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics (admin/debug endpoint)."""
    return manager.get_connection_count()
