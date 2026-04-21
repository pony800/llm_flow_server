from src.api.schemas.response.vo import PathTreeVO
from src.models.enums.com_enum import FileType
from src.core.common import config_manager as path_config
from src.tools import file_tools

async def get_file_tree(file_type: FileType) -> PathTreeVO:
    if file_type == FileType.FLOW:
        return file_tools.build_directory_tree(path_config.PROJECT_PATH, ['json'], path_config.PROJECT_PATH)
    elif file_type == FileType.GGUF:
        return file_tools.build_directory_tree(path_config.GGUF_PATH, ['gguf'], path_config.GGUF_PATH)
    elif file_type == FileType.DATA:
        return file_tools.build_directory_tree(path_config.DATA_PATH, [], path_config.DATA_PATH)
    return PathTreeVO()