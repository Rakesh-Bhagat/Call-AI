from fastapi import APIRouter, WebSocket
from app.live.call import CallSession
from app.transports.browser import BrowserTransport

router = APIRouter()

@router.websocket("/ws/browser")
async def browser_ws(ws: WebSocket):
    await ws.accept()
    await CallSession(BrowserTransport(ws)).run()