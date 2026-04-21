from fastapi import APIRouter, Body
from src.api.controllers import config_controller
from src.api.schemas.request.qo import PathUpdateRequest
from src.api.schemas.response.base_vo import ResultVO

router = APIRouter(tags=["流程执行"])

@router.get("/config/get", summary="获取当前配置")
async def get_config() -> ResultVO:
    """返回当前所有路径配置"""
    return await config_controller.get_config()


@router.post("/config/update", summary="更新项目路径配置")
async def update_paths(request: PathUpdateRequest = Body(...)) -> ResultVO:
    """
    更新项目路径配置

    支持使用 `_BASE_PATH/` 前缀表示项目根目录
    例如: "_BASE_PATH/custom_projects"
    """
    return await config_controller.update_paths(request)


@router.post("/config/reset", summary="重置为默认配置")
async def reset_config() -> ResultVO:
    """重置所有路径为默认配置"""
    return await config_controller.reset_config()