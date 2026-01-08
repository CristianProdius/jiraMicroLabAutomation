"""WebSocket connection manager."""

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from api.websocket.events import WebSocketEvent, EventType


class ConnectionManager:
    """
    Manage WebSocket connections for real-time updates.

    Supports:
    - Job-specific connections (subscribe to updates for a specific job)
    - User-wide connections (receive all updates for a user)
    - Broadcast to all connections
    """

    def __init__(self):
        # job_id -> set of WebSocket connections
        self.job_connections: dict[str, set[WebSocket]] = {}

        # user_id -> set of WebSocket connections
        self.user_connections: dict[int, set[WebSocket]] = {}

        # WebSocket -> (user_id, job_id) mapping for cleanup
        self.connection_info: dict[WebSocket, tuple[int, Optional[str]]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        job_id: Optional[str] = None,
    ) -> None:
        """
        Accept a WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection
            user_id: The authenticated user's ID
            job_id: Optional job ID to subscribe to specific job updates
        """
        await websocket.accept()

        async with self._lock:
            # Register user connection
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

            # Register job connection if provided
            if job_id:
                if job_id not in self.job_connections:
                    self.job_connections[job_id] = set()
                self.job_connections[job_id].add(websocket)

            # Store connection info for cleanup
            self.connection_info[websocket] = (user_id, job_id)

        # Send connected event
        await self.send_personal(
            websocket,
            WebSocketEvent.create(
                EventType.CONNECTED,
                message="Connected to WebSocket",
                user_id=user_id,
                job_id=job_id,
            ),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
        """
        async with self._lock:
            if websocket not in self.connection_info:
                return

            user_id, job_id = self.connection_info[websocket]

            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Remove from job connections
            if job_id and job_id in self.job_connections:
                self.job_connections[job_id].discard(websocket)
                if not self.job_connections[job_id]:
                    del self.job_connections[job_id]

            # Remove connection info
            del self.connection_info[websocket]

    async def send_personal(self, websocket: WebSocket, event: WebSocketEvent) -> bool:
        """
        Send an event to a specific WebSocket.

        Args:
            websocket: The target WebSocket
            event: The event to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(event.model_dump_json())
                return True
        except Exception:
            # Connection might be closed
            await self.disconnect(websocket)
        return False

    async def broadcast_to_job(self, job_id: str, event: WebSocketEvent) -> int:
        """
        Broadcast an event to all connections subscribed to a job.

        Args:
            job_id: The job ID to broadcast to
            event: The event to send

        Returns:
            Number of connections that received the event
        """
        sent_count = 0

        async with self._lock:
            connections = self.job_connections.get(job_id, set()).copy()

        for websocket in connections:
            if await self.send_personal(websocket, event):
                sent_count += 1

        return sent_count

    async def broadcast_to_user(self, user_id: int, event: WebSocketEvent) -> int:
        """
        Broadcast an event to all connections for a user.

        Args:
            user_id: The user ID to broadcast to
            event: The event to send

        Returns:
            Number of connections that received the event
        """
        sent_count = 0

        async with self._lock:
            connections = self.user_connections.get(user_id, set()).copy()

        for websocket in connections:
            if await self.send_personal(websocket, event):
                sent_count += 1

        return sent_count

    async def broadcast_all(self, event: WebSocketEvent) -> int:
        """
        Broadcast an event to all connected WebSockets.

        Args:
            event: The event to send

        Returns:
            Number of connections that received the event
        """
        sent_count = 0

        async with self._lock:
            all_websockets = set(self.connection_info.keys())

        for websocket in all_websockets:
            if await self.send_personal(websocket, event):
                sent_count += 1

        return sent_count

    def get_connection_count(self) -> dict:
        """Get current connection statistics."""
        return {
            "total_connections": len(self.connection_info),
            "users_connected": len(self.user_connections),
            "jobs_subscribed": len(self.job_connections),
        }

    async def cleanup_job(self, job_id: str) -> None:
        """
        Clean up connections for a completed job.

        Removes job-specific subscriptions but keeps user connections alive.
        """
        async with self._lock:
            if job_id in self.job_connections:
                # Update connection info to remove job association
                for websocket in self.job_connections[job_id]:
                    if websocket in self.connection_info:
                        user_id, _ = self.connection_info[websocket]
                        self.connection_info[websocket] = (user_id, None)

                del self.job_connections[job_id]


# Global singleton instance
manager = ConnectionManager()


# Helper functions for easy event emission
async def emit_job_started(
    job_id: str,
    user_id: int,
    jql: str,
    total_issues: int,
    dry_run: bool = False,
) -> None:
    """Emit a JOB_STARTED event."""
    event = WebSocketEvent.create(
        EventType.JOB_STARTED,
        job_id=job_id,
        jql=jql,
        total_issues=total_issues,
        dry_run=dry_run,
    )
    await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)


async def emit_job_progress(
    job_id: str,
    user_id: int,
    current_issue: str,
    processed: int,
    total: int,
    failed: int = 0,
) -> None:
    """Emit a JOB_PROGRESS event."""
    percent = (processed / total * 100) if total > 0 else 0
    event = WebSocketEvent.create(
        EventType.JOB_PROGRESS,
        job_id=job_id,
        current_issue=current_issue,
        processed=processed,
        total=total,
        percent=round(percent, 1),
        failed=failed,
    )
    await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)


async def emit_issue_started(
    user_id: int,
    issue_key: str,
    summary: str,
    job_id: Optional[str] = None,
) -> None:
    """Emit an ISSUE_STARTED event."""
    event = WebSocketEvent.create(
        EventType.ISSUE_STARTED,
        job_id=job_id,
        issue_key=issue_key,
        summary=summary,
    )
    if job_id:
        await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)


async def emit_issue_rubric_complete(
    user_id: int,
    issue_key: str,
    rubric_score: float,
    rubric_breakdown: dict,
    job_id: Optional[str] = None,
) -> None:
    """Emit an ISSUE_RUBRIC_COMPLETE event."""
    event = WebSocketEvent.create(
        EventType.ISSUE_RUBRIC_COMPLETE,
        job_id=job_id,
        issue_key=issue_key,
        rubric_score=rubric_score,
        rubric_breakdown=rubric_breakdown,
    )
    if job_id:
        await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)


async def emit_issue_complete(
    user_id: int,
    issue_key: str,
    score: float,
    emoji: str,
    assessment: str,
    job_id: Optional[str] = None,
) -> None:
    """Emit an ISSUE_COMPLETE event."""
    event = WebSocketEvent.create(
        EventType.ISSUE_COMPLETE,
        job_id=job_id,
        issue_key=issue_key,
        score=score,
        emoji=emoji,
        assessment=assessment,
    )
    if job_id:
        await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)


async def emit_issue_failed(
    user_id: int,
    issue_key: str,
    error: str,
    job_id: Optional[str] = None,
) -> None:
    """Emit an ISSUE_FAILED event."""
    event = WebSocketEvent.create(
        EventType.ISSUE_FAILED,
        job_id=job_id,
        issue_key=issue_key,
        error=error,
    )
    if job_id:
        await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)


async def emit_job_completed(
    job_id: str,
    user_id: int,
    total_processed: int,
    total_failed: int,
    average_score: Optional[float],
    duration_seconds: float,
) -> None:
    """Emit a JOB_COMPLETED event."""
    event = WebSocketEvent.create(
        EventType.JOB_COMPLETED,
        job_id=job_id,
        total_processed=total_processed,
        total_failed=total_failed,
        average_score=average_score,
        duration_seconds=round(duration_seconds, 1),
    )
    await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)
    # Clean up job connections
    await manager.cleanup_job(job_id)


async def emit_job_failed(job_id: str, user_id: int, error: str) -> None:
    """Emit a JOB_FAILED event."""
    event = WebSocketEvent.create(
        EventType.JOB_FAILED,
        job_id=job_id,
        error=error,
    )
    await manager.broadcast_to_job(job_id, event)
    await manager.broadcast_to_user(user_id, event)
    await manager.cleanup_job(job_id)


async def emit_activity(
    user_id: int,
    activity_type: str,
    message: str,
    level: str = "info",
    issue_key: Optional[str] = None,
) -> None:
    """Emit an ACTIVITY event for the live feed."""
    event = WebSocketEvent.create(
        EventType.ACTIVITY,
        type=activity_type,
        message=message,
        level=level,
        issue_key=issue_key,
    )
    await manager.broadcast_to_user(user_id, event)
