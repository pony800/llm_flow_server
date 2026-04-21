from fastapi import APIRouter
from src.api.controllers import node_controller
from src.api.schemas.response.base_vo import ResultVO

router = APIRouter(tags=["节点管理"])

@router.get("/node-data/get", response_model=ResultVO)
async def get_nodes_data():
    return await node_controller.get_nodes_data()