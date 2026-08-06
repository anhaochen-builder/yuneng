"""WebSocket 实时告警推送"""
import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

_connections: set[WebSocket] = set()


@router.websocket("/ws/alarms")
async def ws_alarms(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket 异常: {e}")
    finally:
        _connections.discard(websocket)


async def broadcast_alarm(alarm: dict):
    """向所有连接客户端广播告警"""
    dead = set()
    message = json.dumps({"type": "alarm", "data": alarm}, ensure_ascii=False)
    for ws in _connections:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    _connections -= dead


def get_ws_connections() -> int:
    return len(_connections)
