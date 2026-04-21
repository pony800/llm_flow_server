from fastapi import HTTPException
from src.core.common.config_manager import config_manager, PROJECT_PATH, GGUF_PATH, DATA_PATH
from src.api.schemas.request.qo import PathUpdateRequest
from src.api.schemas.response.base_vo import ResultVO
from src.tools import result_tools


async def get_config() -> ResultVO:



    """返回当前所有路径配置"""
    return result_tools.success({
        "config": config_manager.get_config(),
        "resolved_paths": {
            "project": str(PROJECT_PATH),
            "gguf": str(GGUF_PATH),
            "data": str(DATA_PATH)
        }
    })

async def update_paths(request: PathUpdateRequest) -> ResultVO:
    """
    更新项目路径配置

    支持使用 `_BASE_PATH/` 前缀表示项目根目录
    例如: "_BASE_PATH/custom_projects"
    """
    try:
        config_manager.update_paths(
            project=request.project,
            gguf=request.gguf,
            data=request.data
        )

        return result_tools.success({
            "new_config": config_manager.get_config(),
            "resolved_paths": {
                "project": str(PROJECT_PATH),
                "gguf": str(GGUF_PATH),
                "data": str(DATA_PATH)
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

async def reset_config() -> ResultVO:
    """重置所有路径为默认配置"""
    try:
        base_path = config_manager._base_path
        config_manager.update_paths(
            project=str(base_path / "projects"),
            gguf=str(base_path / "models/gguf"),
            data=str(base_path / "data")
        )

        return result_tools.success({
            "status": "success",
            "message": "配置已重置为默认值",
            "config": config_manager.get_config()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")
