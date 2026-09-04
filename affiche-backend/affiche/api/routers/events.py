import asyncio
import json
import logging

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from affiche.app.events import event_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/stream")
async def event_stream():

    async def generate():
        queue = event_manager.subscribe()
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
        finally:
            event_manager.unsubscribe(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
