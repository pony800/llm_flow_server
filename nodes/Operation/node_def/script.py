from types import CodeType
from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.core.common.constant import STOP_HANDLE_NAME
from src.models.enums.vue_flow_enum import ParamType
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowOutputParam, FlowInputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    code: str | CodeType = """# ------------------------------------------
# 1. 该节点定义的输入输出参数已注入到python上下文环境中可直接读取或赋值
# 2. 对于每一个python解释器环境都提供了一个独立的字典类型的 data 永久存储变量, 存储在该变量中的值不会被删除
# 3. 在当前python解释器环境中提供一个bool类型的 is_continue 变量(默认值为True), 主动将其设置为 False 时程序将不会执行后续节点
# ------------------------------------------
# 示例:
# 显式的将 is_continue 设置为 False 会跳过后续节点(如果该SCRIPT节点在循环内则直接开始下一个循环)
# is_continue = False

# 示例:记录并输出当前是第几次执行
if "count" not in data:
    data["count"] = 1
else:
    data["count"] += 1
count.value = data["count"]
    """
    data: dict = {}
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Script(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        await ws.send_json(WsMessageTool.position(context))
        content:Content = context.content
        returnParam = ReturnParam()

        try:
            env = dict()
            # 将输入输出参数拆包到环境中
            for param_name, var in context.input_map.items():
                env[param_name] = var.value
            for param_name, var in context.output_map.items():
                env[param_name] = var.value
            env["data"] = content.data
            env["is_continue"] = True
            # 执行脚本
            exec(content.code, env)
            # 将环境中的变量封包到输入输出中
            for param_name, var in context.input_map.items():
                var.value = env[param_name]
            for param_name, var in context.output_map.items():
                var.value = env[param_name]
            content.data = env["data"]
            if not env["is_continue"]:
                returnParam.handler_name = STOP_HANDLE_NAME

        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))
            print(e)
            raise e

        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        messages:List[str] = []
        for param in params:
            if param.name in ["data", "is_continue"]:
                messages.append("入参中不应定义data或is_continue")
                break
        for param in returns:
            if param.name in ["data", "is_continue"]:
                messages.append("返回值中不应定义data或is_continue")
                break
        if content.code is None or content.code == "":
            messages.append("未编写有效代码")
        try:
            content.code = compile(content.code, '<string>', 'exec')
        except Exception as e:
            messages.append(f"代码编译失败,原因:{str(e)}")
        return content, messages

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "SCRIPT"
        node_data.label = "Python脚本执行器"
        node_data.desc = "1.在该节点定义的输入输出参数已注入到python上下文环境中可直接读取或赋值\n2.对于每一个python解释器环境都提供了一个独立的字典类型的'data'变量,该变量中记录的值在下次运行到该节点时仍存在\n3.在当前python解释器环境中提供一个bool类型的'is_continue'变量(默认值为True),主动将其设置为'False'时程序将不会执行后续节点\n4.具体使用可以参考默认示例"
        node_data.content = Content()
        node_data.canAddParams = True
        node_data.canAddReturns = True
        # 输入参数
        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "count"
        out1.type = ParamType.int
        out1.editable = True
        node_data.returns.append(out1)
        # 连接器
        return node_data