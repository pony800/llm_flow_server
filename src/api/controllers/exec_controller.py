from fastapi import WebSocket
from src.core.engine.progress import Progress
from src.core.nodes.node_loader import node_loader
from src.core.websocket.websocket_agent import WebSocketAgent

async def handle_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        ws_agent = WebSocketAgent(websocket)
        file_path = await websocket.receive_text()
        start_id = await websocket.receive_text()
        progress = Progress(node_loader=node_loader, ws=ws_agent)
        if not await progress.open_flow(file_path):
            return
        await progress.exec(start_id)
    finally:
        await websocket.close()