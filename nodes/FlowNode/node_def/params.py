from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Params(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        try:
            pass
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))

        returnParam = ReturnParam()
        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "PARAMS"
        node_data.label = "参数定义"
        node_data.desc = "每次运行到此处都会重新对变量进行初始化操作"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = True
        # 输入参数
        # 输出参数
        # 连接器
        return node_data