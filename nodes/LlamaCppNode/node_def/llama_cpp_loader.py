from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.common.config_manager import GGUF_PATH
from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from llama_cpp import Llama


class Content(BaseModel):
    llm_model: Llama | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class LlamaCppLoader(NodeInterface):
    """
    输入参数:
        gguf       [gguf]     :从这里开始循环(计数器初始值)
        prompt     [string]   :当计数器大于等于endWith时结束循环
    输出参数:
        gguf     [output]   :当前循环计数器值
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
            if content.llm_model is None:
                path = GGUF_PATH / context.input_map["gguf"].value
                content.llm_model = Llama(
                    model_path=str(path),
                    n_ctx=context.input_map["n_ctx"].value,
                    n_gpu_layers=999,  # 设置大于总层数的值强制全层卸载（比-1更可靠）
                    n_batch=512,  # 减小批处理尺寸（降低显存碎片）
                    cache_implementation="gpu",  # 显式指定缓存设备
                    offload_kv=False,  # 禁用KV缓存回退
                    flash_attn=True,  # 确保编译时启用FlashAttention支持
                    # 关键性能参数
                    n_threads=24,  # 根据CPU物理核心数调整（建议总线程数=物理核心数）
                    tensor_split=[100],  # 显式指定空列表强制单卡全占用
                    # 禁用非必要计算
                    logits_all=False,
                    embedding=False,
                    # 硬件加速参数
                    mul_mat_q=True,  # 启用矩阵乘法加速
                    rope_scaling="linear",  # 显式指定RoPE缩放方式（对齐模型训练配置）
                    verbose=False  # 关闭日志
                )
                context.output_map["llamaLlmModel"].value = content.llm_model
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
        node_data.type = "LLAMA_CPP_LOADER"
        node_data.label = "加载gguf格式llm大模型"
        node_data.desc = "1.在显存足够的情况下优先将模型的所有层加载到显存\n2.在流程运行到此处时模型会被加载且一直保留到运行结束,期间无法手动卸载模型\n3.显存不足时会自动尝试卸载部分层到内存\n4.使用多个节点加载多个模型时先加载的模型优先进入显存\n注:在多个位置使用同一个模型进行生成只需加载一次"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        #输入参数
        param1 = FlowInputParam()
        param1.name = "gguf"
        param1.desc = "选择gguf格式llm模型"
        param1.typeDef = "gguf"
        param1.type = ParamType.gguf
        param1.require = True
        param1.value = ""
        param1.switch = InputSwitch.FILE
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "n_ctx"
        param2.desc = "上下文长度(过高的上下文长度可能导致模型卸载到内存)"
        param2.typeDef = "Integer"
        param2.type = ParamType.int
        param2.require = True
        param2.value = 16384
        param2.switch = InputSwitch.INT
        node_data.params.append(param2)
        #输出参数
        out1 = FlowOutputParam()
        out1.name = "llamaLlmModel"
        out1.type = "LlmModel"
        out1.typeDef = "LlmModel"
        out1.desc = "已加载的llm模型"
        node_data.returns.append(out1)
        #连接器
        return node_data
