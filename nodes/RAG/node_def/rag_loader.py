import os
from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from nodes.RAG.croe.model import RagData
from nodes.RAG.croe.rag import RAGService
from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.common.config_manager import GGUF_PATH, DATA_PATH
from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from llama_cpp import Llama


class Content(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RagLoader(NodeInterface):
    """
    """
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError(f"context.content is not of type Content {context.label}")
        content: Content = context.content
        await ws.send_json(WsMessageTool.position(context))

        return_param = ReturnParam()
        return_param.is_finish = True
        try:
            rag_data = RagData()
            context.output_map["rag"].value = rag_data
            # 如果用户填写了数据库路径则按路径加载, 如果用户选择了数据库文件则按文件加载(文件优先)
            if context.input_map["dbFile"].value != "":
                rag_data.rag_service = RAGService(DATA_PATH / context.input_map["dbFile"].value)
            elif context.input_map["dbPath"].value != "":
                if context.input_map["dbPath"].value.endswith(".db"):
                    rag_data.rag_service = RAGService(DATA_PATH / context.input_map["dbPath"].value)
                else:
                    await ws.send_json(WsMessageTool.error(context, "数据库文件扩展名必须为db"))
                    return ReturnParam()
            else:
                await ws.send_json(WsMessageTool.error(context, "未指定数据库文件"))
                return ReturnParam()
            # 初始化
            rag_data.rag_service.create_knowledge_base()
            # 如果用户选择了词嵌入模型则加载它
            if context.input_map["gguf"].value != "":
                path = GGUF_PATH / context.input_map["gguf"].value
                rag_data.embedding_model = Llama(
                    model_path=str(path),
                    embedding=True,
                    n_ctx=512,
                    # 彻底禁用GPU的配置
                    n_gpu_layers=0,  # 0层使用GPU
                    main_gpu=0,
                    tensor_split=[],
                    # 内存控制
                    use_mmap=False,
                    use_mlock=True,
                    # CPU优化
                    n_threads=max(1, os.cpu_count() - 1),  # 保留一个核心给系统
                    n_batch=512,
                    # 禁用非必要功能
                    flash_attn=False,
                    logits_all=False,
                    vocab_only=False,
                    verbose=False
                )
            else:
                # 目前暂不支持外挂模型
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
        node_data.type = "RAG_LOADER"
        node_data.label = "加载向量数据库"
        node_data.desc = "为大模型提供检索增强服务(基于python-sqlite3实现python原生轻量向量数据库)\n1.支持语义相似度匹配(使用余弦相似度)和数据标签\n2.支持使用内存缓存进行检索加速,支持1秒内10万级别数据检索"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        #输入参数
        param1 = FlowInputParam()
        param1.name = "gguf"
        param1.type = ParamType.gguf
        param1.desc = "选择词嵌入模型文件"
        param1.typeDef = "gguf"
        param1.require = True
        param1.editable = False
        param1.value = ""
        param1.switch = InputSwitch.FILE
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "dbFile"
        param2.type = 'db'
        param2.desc = "选择数据库文件(与dbPath二选一填写)"
        param2.typeDef = "db"
        param2.require = False
        param2.editable = False
        param2.value = ""
        param2.switch = InputSwitch.FILE
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "dbPath"
        param3.type = ParamType.string
        param3.desc = "保存数据库文件到(与dbFile二选一填写)"
        param3.typeDef = "String"
        param3.require = False
        param3.editable = False
        param3.value = ""
        param3.switch = InputSwitch.VALUE
        node_data.params.append(param3)

        param4 = FlowInputParam()
        param4.name = "cacheSize"
        param4.type = ParamType.int
        param4.desc = "允许使用的内存缓存大小Mb"
        param4.typeDef = "int"
        param4.require = True
        param4.editable = False
        param4.value = 1024
        param4.switch = InputSwitch.INT
        node_data.params.append(param4)

        #输出参数
        out1 = FlowOutputParam()
        out1.name = "rag"
        out1.type = "Rag"
        node_data.returns.append(out1)
        #连接器
        return node_data
