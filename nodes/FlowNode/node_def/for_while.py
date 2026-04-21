from types import CodeType
from typing import Tuple, List

from pydantic import BaseModel, ConfigDict
from src.models.enums.vue_flow_enum import ParamType
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowOutputParam, FlowOutputHandle, FlowInputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    condition: str | CodeType = ""  #循环条件
    count: int = 0    #循环计数器

    model_config = ConfigDict(arbitrary_types_allowed=True)

class ForWhile(NodeInterface):
    """
    输出参数:
        count        [int]        :当前循环计数器值
    连接器:
        for                         :当需要继续循环时激活该连接器,否则激活默认连接器
    """
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        returnParam = ReturnParam()

        try:
            env = dict()
            for param_name, var in context.input_map.items():
                env[param_name] = var.value
            if eval(content.condition, env):
                #进入循环
                content.count += 1
                context.output_map["count"].value = content.count
                returnParam.is_finish = False
                returnParam.handler_name = "while"
                return returnParam
            else:
                #退出循环
                context.output_map["count"].value = content.count
                content.count = 0
                returnParam.is_finish = True
                return returnParam
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))

        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        messages: List[str] = []
        try:
            content.condition = compile(content.condition, '<string>', 'eval')
        except Exception as e:
            messages.append(f"条件:'{content.condition}'编译失败')原因:{str(e)}")
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "FOR_WHILE"
        node_data.label = "while循环"
        node_data.desc = "注:当循环执行完成后会继续执行与结束连接器相连的节点"
        node_data.content = Content()
        node_data.canAddParams = True
        node_data.canAddReturns = False
        # 输入参数
        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "count"
        out1.desc = "当前循环次数"
        out1.typeDef = "Integer"
        out1.type = ParamType.int
        out1.editable = False
        node_data.returns.append(out1)
        # 连接器
        handle1 = FlowOutputHandle()
        handle1.name = "while"
        handle1.label = "while循环"
        node_data.handles.append(handle1)
        return node_data