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


class RagSearch(NodeInterface):
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
        await ws.send_json(WsMessageTool.position(context))

        returnParam = ReturnParam()
        try:
            rag_data: RagData = context.input_map["rag"].value
            if rag_data.rag_service is None:
                await ws.send_json(WsMessageTool.error(context, "向量数据库未成功加载"))
            if rag_data.embedding_model is not None:
                # 使用自身的模型进行向量化
                if context.input_map["keyContent"].value is None:
                    await ws.send_json(WsMessageTool.error(context, "key值为空"))
                vec: list[float] = rag_data.embedding_model.create_embedding(context.input_map["keyContent"].value)['data'][0]['embedding']
                if vec is None or len(vec) == 0:
                    await ws.send_json(WsMessageTool.error(context, "计算嵌入向量出错"))
                context.output_map["searchResult"].value = rag_data.rag_service.search_data(
                    query_vec=vec,
                    top_k=context.input_map["top_k"].value,
                    top_p=context.input_map["top_p"].value,
                    target_labels=context.input_map["targetLabels"].value,
                    exclude_labels=context.input_map["excludeLabels"].value)
                print(context.output_map["searchResult"].value)
            else:
                # 使用外部模型进行向量化
                pass
            return returnParam
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))
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
        #基本信息
        node_data = NodeData()
        node_data.type = "RAG_SEARCH"
        node_data.label = "进行向量匹配查询"
        node_data.desc = "从向量数据库中查询"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        #输入参数
        param1 = FlowInputParam()
        param1.name = "rag"
        param1.type = "Rag"
        param1.require = True
        param1.editable = False
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
        param1.editable = False
        param2.switch = InputSwitch.PATH
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "top_k"
        param3.type = ParamType.int
        param3.typeDef = "int"
        param3.value = 10
        param3.desc = "返回库中匹配的前top_k个内容"
        param3.require = True
        param1.editable = False
        param3.switch = InputSwitch.INT
        node_data.params.append(param3)

        param4 = FlowInputParam()
        param4.name = "top_p"
        param4.type = ParamType.float
        param4.typeDef = "float"
        param4.value = 0.7
        param4.desc = "返回库中余弦匹配相似度不低于top_p的数据"
        param4.require = True
        param1.editable = False
        param4.switch = InputSwitch.FLOAT
        node_data.params.append(param4)

        param5 = FlowInputParam()
        param5.name = "targetLabels"
        param5.type = ParamType.list
        param5.typeDef = "List<String>"
        param5.value = None
        param5.desc = "检索包含上述所有标签的数据"
        param5.require = False
        param1.editable = False
        param5.switch = InputSwitch.PATH
        node_data.params.append(param5)

        param6 = FlowInputParam()
        param6.name = "excludeLabels"
        param6.type = ParamType.list
        param6.typeDef = "List<String>"
        param6.value = None
        param6.desc = "检索不包含上述任何一个标签的数据"
        param6.require = False
        param1.editable = False
        param6.switch = InputSwitch.PATH
        node_data.params.append(param6)

        #输出参数
        out1 = FlowOutputParam()
        out1.name = "searchResult"
        out1.desc = "检索结果"
        out1.typeDef = "list<{id:Long(数据自增id), similarity:Double(匹配相似度), content:String(内容), labels:List<String>(标签列表)}>"
        out1.type = ParamType.list
        node_data.returns.append(out1)
        #连接器
        return node_data
