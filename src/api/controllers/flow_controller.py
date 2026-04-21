import os
import shutil
from pathlib import Path
from src.models.computation.vue_flow import FlowContext, FlowInputParam
from src.api.schemas.response.base_vo import ResultVO
from src.core.common import config_manager as path_config
from src.models.enums.vue_flow_enum import InputSwitch
from src.tools import result_tools

async def add_flow(file_path: str, label: str) -> ResultVO:
    flow = FlowContext()
    flow.label = label
    flow.filePath = file_path

    full_path = path_config.PROJECT_PATH / file_path
    if os.path.exists(full_path):
        return result_tools.fail(f"文件已存在:{full_path}")

    full_path.parent.mkdir(parents=True, exist_ok=True)

    if full_path.suffix.lower() != '.json':
        return result_tools.fail("文件扩展名必须是 .json")

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(flow.model_dump_json(indent=4))
    return result_tools.success(True)


async def update_flow(flow: FlowContext) -> ResultVO:
    full_path = path_config.PROJECT_PATH / flow.filePath
    if not os.path.exists(full_path):
        return result_tools.fail(f"文件不存在:{full_path}")

    if full_path.suffix.lower() != '.json':
        return result_tools.fail("文件扩展名必须是 .json")

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(flow.model_dump_json(indent=4))
    return result_tools.success({"absolute_path": str(full_path)})


async def delete_flow(file_path: str) -> ResultVO:
    full_path: Path = path_config.PROJECT_PATH / file_path

    # 检查路径是否存在
    if not full_path.exists():
        return result_tools.fail(f"路径不存在: {full_path}")

    try:
        # 处理文件删除
        if full_path.is_file():
            if full_path.suffix.lower() != '.json':
                return result_tools.fail("文件扩展名必须是 .json")
            os.remove(full_path)

        # 处理文件夹删除
        elif full_path.is_dir():
            shutil.rmtree(full_path)

        return result_tools.success(None)

    except FileNotFoundError:
        return result_tools.fail(f"路径不存在: {full_path}")
    except PermissionError:
        return result_tools.fail(f"没有权限删除路径: {full_path}")
    except OSError as e:
        return result_tools.fail(f"系统错误: {e}")
    except Exception as e:
        return result_tools.fail(f"删除操作时发生意外错误: {e}")

async def copy_flow(file_path: str, new_file_path: str, label: str) -> ResultVO:
    full_path = path_config.PROJECT_PATH / file_path
    if not os.path.exists(full_path):
        return result_tools.fail(f"文件不存在:{full_path}")

    if full_path.suffix.lower() != '.json':
        return result_tools.fail("复制文件的扩展名必须是.json")

    with open(full_path, 'r', encoding='utf-8') as f:
        json_data = f.read()

    flow = FlowContext.model_validate_json(json_data)
    flow.label = label
    flow.filePath = new_file_path

    full_path = path_config.PROJECT_PATH / new_file_path
    if os.path.exists(full_path):
        return result_tools.fail(f"文件已存在:{full_path}")

    full_path.parent.mkdir(parents=True, exist_ok=True)

    if full_path.suffix.lower() != '.json':
        return result_tools.fail("文件扩展名必须是 .json")

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(flow.model_dump_json(indent=4))
    return result_tools.success(True)

async def rename_flow(file_path: str, new_file_path: str) -> ResultVO:
    # 读取文件并校验
    full_path = path_config.PROJECT_PATH / file_path
    new_full_path = path_config.PROJECT_PATH / new_file_path
    if not os.path.exists(full_path):
        return result_tools.fail(f"文件不存在:{full_path}")
    if full_path.suffix.lower() != '.json' or new_full_path.suffix.lower() != '.json':
        return result_tools.fail("文件扩展名必须是 .json")
    with open(full_path, 'r', encoding='utf-8') as f:
        json_data = f.read()
    # 重新保存文件
    flow = FlowContext.model_validate_json(json_data)
    flow.filePath = new_file_path
    if os.path.exists(new_full_path):
        return result_tools.fail(f"文件已存在:{new_full_path}")
    new_full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(new_full_path, 'w', encoding='utf-8') as f:
        f.write(flow.model_dump_json(indent=4))
    # 删除源文件
    await delete_flow(file_path)
    return result_tools.success(True)



async def get_flow(file_path: str) -> ResultVO:
    full_path = path_config.PROJECT_PATH / file_path
    if not os.path.exists(full_path):
        return result_tools.fail(f"文件不存在:{full_path}")

    if full_path.suffix.lower() != '.json':
        return result_tools.fail("文件扩展名必须是 .json")

    with open(full_path, 'r', encoding='utf-8') as f:
        json_data = f.read()
    return result_tools.success(FlowContext.model_validate_json(json_data))

async def get_flow_info(file_path: str) -> ResultVO:
    full_path = path_config.PROJECT_PATH / file_path
    if not os.path.exists(full_path):
        return result_tools.fail(f"文件不存在:{full_path}")

    if full_path.suffix.lower() != '.json':
        return result_tools.fail("文件扩展名必须是 .json")

    with open(full_path, 'r', encoding='utf-8') as f:
        json_data = f.read()
    flow_data = FlowContext.model_validate_json(json_data)

    params :list[FlowInputParam] = []
    for param in flow_data.params:
        copy:FlowInputParam = FlowInputParam()
        copy.name = param.name
        copy.type = param.type
        copy.typeDef = param.typeDef
        copy.desc = param.desc
        copy.path = []
        copy.require = True
        copy.switch = InputSwitch.PATH
        copy.editable = False
        copy.value = None
        params.append(copy)

    return result_tools.success({
        'params': params,
        'returns': flow_data.returns,
        'label': flow_data.label,
    })
