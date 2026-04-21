from fastapi import APIRouter, WebSocket
from src.api.controllers import exec_controller

router = APIRouter(tags=["流程执行"])
@router.websocket("/exec")
async def websocket_endpoint(websocket: WebSocket):
    await exec_controller.handle_websocket(websocket)