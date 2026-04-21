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


class RagAdd(NodeInterface):
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
            if rag_data.embedding_model is not None:
                # 使用自身的模型进行向量化
                if context.input_map["keyContent"].value is None:
                    await ws.send_json(WsMessageTool.error(context, "key值为空"))
                vec: list[float] = rag_data.embedding_model.create_embedding(context.input_map["keyContent"].value)['data'][0]['embedding']
                con: str = context.input_map["content"].value
                if vec is None or len(vec) == 0:
                    await ws.send_json(WsMessageTool.error(context, "计算嵌入向量出错"))
                if con is None or con == "":
                    await ws.send_json(WsMessageTool.error(context, "保存的内容为空"))
                labels:list[str] = context.input_map["labels"].value
                rag_data.rag_service.insert_data([(vec, con, labels)])
            else:
                # 使用外部的模型进行向量化
                pass
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
        node_data.type = "RAG_ADD"
        node_data.label = "向rag数据库中添加一条数据"
        node_data.desc = "向指定rag数据库中添加一条数据"
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
        param2.name = "keyContent"
        param2.type = ParamType.string
        param2.typeDef = "string"
        param2.desc = "需要被向量化检索的内容(key值)"
        param2.require = True
        param2.switch = InputSwitch.PATH
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "content"
        param3.desc = "被保存的内容"
        param3.type = ParamType.string
        param3.typeDef = "string"
        param3.require = True
        param3.switch = InputSwitch.PATH
        node_data.params.append(param3)

        param4 = FlowInputParam()
        param4.name = "labels"
        param4.desc = "数据标签"
        param4.type = ParamType.list
        param4.typeDef = "List<String>"
        param4.require = False
        param4.switch = InputSwitch.PATH
        node_data.params.append(param4)

        #连接器
        return node_data
