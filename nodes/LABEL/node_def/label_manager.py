from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

class LabelManager(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content: Content = context.content

        returnParam = ReturnParam()
        returnParam.is_finish = True
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
        node_data = NodeData()
        node_data.type = "LABEL_MANAGER"
        node_data.label = "标签管理器"
        node_data.desc = "标签管理自动任务"
        node_data.hasStart = False
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        return node_data