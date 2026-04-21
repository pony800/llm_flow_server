from fastapi import APIRouter, Query, Body, WebSocket
from src.api.controllers import flow_controller
from src.api.schemas.response.base_vo import ResultVO
from src.models.computation.vue_flow import FlowContext

router = APIRouter(tags=["流程管理"])

@router.post("/flow/add")
async def add_flow(
    file_path: str = Query(...),
    label: str = Query(...)
) -> ResultVO:
    return await flow_controller.add_flow(file_path, label)

@router.post("/flow/update")
async def update_flow(flow: FlowContext = Body(...)) -> ResultVO:
    return await flow_controller.update_flow(flow)

@router.post("/flow/delete")
async def delete_flow(file_path: str = Query(...)) -> ResultVO:
    return await flow_controller.delete_flow(file_path)

@router.post("/flow/copy")
async def copy_flow(file_path: str = Query(...), new_file_path: str = Query(...), label: str = Query(...)) -> ResultVO:
    return await flow_controller.copy_flow(file_path, new_file_path, label)

@router.post("/flow/rename")
async def rename_flow(file_path: str = Query(...), new_file_path: str = Query(...)) -> ResultVO:
    return await flow_controller.rename_flow(file_path, new_file_path)

@router.get("/flow/get")
async def get_flow(file_path: str = Query(...)) -> ResultVO:
    return await flow_controller.get_flow(file_path)

@router.get("/flow/info")
async def get_flow_info(file_path: str = Query(...)) -> ResultVO:
    return await flow_controller.get_flow_info(file_path)