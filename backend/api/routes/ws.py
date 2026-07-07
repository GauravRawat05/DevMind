"""WebSocket route for streaming real-time analysis progress to clients.

Subscribes to the Redis Pub/Sub channel ``job_progress:{job_id}`` and
forwards every progress event to the connected WebSocket client until
the job reaches a terminal state (``completed`` or ``failed``) or the
client disconnects.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.database import redis_client

logger = logging.getLogger("devmind.api.ws")

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str) -> None:
    """Stream analysis progress for *job_id* over a WebSocket connection.

    The endpoint:

    1. Accepts the WebSocket handshake.
    2. Subscribes to the Redis Pub/Sub channel ``job_progress:<job_id>``.
    3. Forwards every published message to the client as a JSON text frame.
    4. Terminates the loop when a message with ``status`` equal to
       ``"completed"`` or ``"failed"`` is received, or when the client
       disconnects.
    """
    await websocket.accept()
    logger.info("WebSocket connected for job %s", job_id)

    channel_name = f"job_progress:{job_id}"
    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(channel_name)
        logger.info("Subscribed to Redis Pub/Sub channel: %s", channel_name)

        # Send an initial acknowledgement so the client knows we're listening
        await websocket.send_json({
            "job_id": job_id,
            "stage": "connected",
            "message": "WebSocket connected. Listening for progress updates...",
            "status": "connected",
        })

        while True:
            # Poll for messages with a short timeout to allow checking
            # for WebSocket disconnection
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message and message["type"] == "message":
                data_str = message["data"]
                # data might be bytes or str depending on decode_responses
                if isinstance(data_str, bytes):
                    data_str = data_str.decode("utf-8")

                try:
                    payload = json.loads(data_str)
                except json.JSONDecodeError:
                    payload = {"message": data_str}

                # Forward the progress event to the client
                await websocket.send_json(payload)
                logger.debug("Forwarded progress to WebSocket for job %s: %s", job_id, payload.get("stage", "?"))

                # Check for terminal state
                msg_status = payload.get("status", "")
                if msg_status in ("completed", "failed"):
                    logger.info(
                        "Job %s reached terminal state '%s'. Closing WebSocket.",
                        job_id, msg_status,
                    )
                    break

            # Brief yield to prevent tight-loop CPU spin
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for job %s", job_id)
    except Exception as exc:
        logger.error("WebSocket error for job %s: %s", job_id, exc)
        try:
            await websocket.send_json({
                "job_id": job_id,
                "stage": "error",
                "message": f"Server error: {exc}",
                "status": "error",
            })
        except Exception:
            pass  # Client may already be disconnected
    finally:
        # Clean up the Pub/Sub subscription
        try:
            await pubsub.unsubscribe(channel_name)
            await pubsub.aclose()
        except Exception:
            pass
        logger.info("WebSocket cleanup complete for job %s", job_id)
