from fastapi import APIRouter, Request, Response, WebSocket
from app.live.call import CallSession
from app.transports.twillio import TwillioTransport

router = APIRouter()

@router.post("/twiml")
async def twiml(request: Request):
    host = request.headers["host"]
    print("Twillio host: ", host)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Connect><Stream url="wss://{host}/ws/twillio"/></Connect>'
        "<Hangup/>"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")

@router.websocket("/ws/twillio")
async def twillio_ws(ws: WebSocket):
    await ws.accept()
    await CallSession(TwillioTransport(ws)).run()