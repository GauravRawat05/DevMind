"""Integration tests for WebSocket streaming endpoint.

Tests verify that the /ws/{job_id} WebSocket endpoint:
- Accepts connections and sends initial acknowledgement
- Receives and forwards Redis Pub/Sub messages
- Closes cleanly on terminal states
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.testclient import TestClient

from backend.main import app


@pytest.mark.asyncio
class TestWebSocket:
    """Verify WebSocket endpoint behavior."""

    async def test_websocket_connection_and_ack(self) -> None:
        """WebSocket /ws/{job_id} should accept connection and send acknowledgement."""
        # Mock Redis pubsub so the test doesn't depend on a live Redis connection
        # (the event loop may be closed after prior API integration tests)
        async def mock_get_message(ignore_subscribe_messages=True, timeout=1.0):
            return None

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.aclose = AsyncMock()
        mock_pubsub.get_message = mock_get_message

        with patch("backend.api.routes.ws.redis_client") as mock_redis:
            mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

            client = TestClient(app)
            with client.websocket_connect("/ws/test-job-123") as websocket:
                # Should receive the initial acknowledgement message
                data = websocket.receive_json()
                assert data["job_id"] == "test-job-123"
                assert data["stage"] == "connected"
                assert data["status"] == "connected"
                assert "Listening for progress updates" in data["message"]

    async def test_websocket_receives_progress_and_closes_on_complete(self) -> None:
        """WebSocket should forward Redis Pub/Sub messages and close on terminal state."""
        progress_messages = [
            {
                "type": "message",
                "data": json.dumps({
                    "job_id": "test-job-456",
                    "stage": "fetching",
                    "message": "Downloading repository...",
                    "status": "in_progress",
                }),
            },
            {
                "type": "message",
                "data": json.dumps({
                    "job_id": "test-job-456",
                    "stage": "complete",
                    "message": "Analysis complete!",
                    "status": "completed",
                }),
            },
        ]

        call_count = 0

        async def mock_get_message(ignore_subscribe_messages=True, timeout=1.0):
            nonlocal call_count
            if call_count < len(progress_messages):
                msg = progress_messages[call_count]
                call_count += 1
                return msg
            return None

        # Build a mock pubsub object. redis_client.pubsub() is a regular
        # (non-async) method that returns an object with async methods.
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub.aclose = AsyncMock()
        mock_pubsub.get_message = mock_get_message

        with patch("backend.api.routes.ws.redis_client") as mock_redis:
            # pubsub() is a regular method returning our mock object
            mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

            client = TestClient(app)
            with client.websocket_connect("/ws/test-job-456") as websocket:
                # 1. Initial ack
                ack = websocket.receive_json()
                assert ack["stage"] == "connected"

                # 2. First progress message (fetching)
                msg1 = websocket.receive_json()
                assert msg1["stage"] == "fetching"
                assert msg1["status"] == "in_progress"

                # 3. Terminal message (completed) — should close after this
                msg2 = websocket.receive_json()
                assert msg2["stage"] == "complete"
                assert msg2["status"] == "completed"

    async def test_websocket_handles_failed_state(self) -> None:
        """WebSocket should close on 'failed' terminal state."""
        fail_message = {
            "type": "message",
            "data": json.dumps({
                "job_id": "test-job-789",
                "stage": "error",
                "message": "Pipeline failed: API rate limit exceeded",
                "status": "failed",
            }),
        }

        call_count = 0

        async def mock_get_message(ignore_subscribe_messages=True, timeout=1.0):
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return fail_message
            return None

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub.aclose = AsyncMock()
        mock_pubsub.get_message = mock_get_message

        with patch("backend.api.routes.ws.redis_client") as mock_redis:
            mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

            client = TestClient(app)
            with client.websocket_connect("/ws/test-job-789") as websocket:
                # 1. Initial ack
                ack = websocket.receive_json()
                assert ack["stage"] == "connected"

                # 2. Error message — should close after this
                msg = websocket.receive_json()
                assert msg["stage"] == "error"
                assert msg["status"] == "failed"
                assert "rate limit" in msg["message"]
