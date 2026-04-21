from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from nodes.RAG.croe.model import RagData
from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RagDelete(NodeInterface):
    """
    输入参数:
        gguf       [output]     :从这里开始循环(计数器初始值)
        prompt     [string]   :当计数器大于等于endWith时结束循环
    输出参数:
        output     [string]   :当前循环计数器值
    连接器:
    """
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError(f"context.content is not of type Content {context.label}")
        content: Content = context.content

        return_param = ReturnParam()
        try:
            rag_data: RagData = context.input_map["rag"].value
            if rag_data.rag_service is None:
                await ws.send_json(WsMessageTool.error(context, "向量数据库未成功加载"))
            rag_data.rag_service.delete_data([context.input_map["id"].value])
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))
        return_param.is_finish = True
        return return_param

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        #基本信息
        node_data = NodeData()
        node_data.type = "RAG_DELETE"
        node_data.label = "从rag数据库删除一条数据"
        node_data.desc = "删除指定数据id的数据"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        #输入参数
        param1 = FlowInputParam()
        param1.name = "rag"
        param1.type = "Rag"
        param1.require = True
        param1.typeDef = "rag"
        param1.desc = "请选择RAG_LOADER节点返回的RAG数据库"
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "id"
        param2.type = ParamType.int
        param2.typeDef = "Long"
        param2.desc = "需要被删除的数据id"
        param2.require = True
        param2.switch = InputSwitch.PATH
        node_data.params.append(param2)

        #连接器
        return node_data
