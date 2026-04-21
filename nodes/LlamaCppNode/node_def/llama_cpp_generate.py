from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from llama_cpp import Llama


class Content(BaseModel):
    output: str = ""
    llm_model: Llama | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class LlamaGenerate(NodeInterface):
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
            if content.llm_model is None:
                content.llm_model = context.input_map["llamaLlmModel"].value

            stream = content.llm_model.create_completion(
                context.input_map["prompt"].value,
                max_tokens=context.input_map["maxTokens"].value,
                temperature=context.input_map["temperature"].value,
                top_p=context.input_map["top-p"].value,
                top_k=context.input_map["top-k"].value,
                stop=context.input_map["stop"].value.split(),
                stream=True  # 启用流式输出
            )

            re = ""
            for output in stream:
                word = output["choices"][0]["text"]
                re = re + word
                await ws.send_json(WsMessageTool.add(context, "text", word))
            context.output_map["output"].value = re

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
        node_data.type = "LLAMA_GENERATE"
        node_data.label = "使用大模型进行生成"
        node_data.desc = "1.生成使用单次对话generate模式,通过不同提示词给模型赋予不同的能力\n2.模型生成内容时页面会切换至大模型生成页面,且生成结束后不做停留"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        #输入参数
        param1 = FlowInputParam()
        param1.name = "llamaLlmModel"
        param1.type = "LlmModel"
        param1.typeDef = "LlmModel"
        param1.desc = "请选择模型加载节点返回的模型对象"
        param1.require = True
        param1.path = []
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "prompt"
        param2.desc = "模型提示词"
        param2.typeDef = "String"
        param2.type = ParamType.string
        param2.require = True
        param2.path = []
        param2.switch = InputSwitch.PATH
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "maxTokens"
        param3.desc = "模型最大输出长度"
        param3.typeDef = "Integer"
        param3.type = ParamType.int
        param3.require = True
        param3.value = 1000
        param3.switch = InputSwitch.INT
        node_data.params.append(param3)

        param4 = FlowInputParam()
        param4.name = "temperature"
        param4.desc = "模型温度(0-2)"
        param4.typeDef = "Float"
        param4.type = ParamType.float
        param4.require = True
        param4.value = 0.7
        param4.switch = InputSwitch.FLOAT
        node_data.params.append(param4)

        param5 = FlowInputParam()
        param5.name = "top-k"
        param5.desc = "保留分布概率最高的词个数"
        param5.typeDef = "Integer"
        param5.type = ParamType.int
        param5.require = True
        param5.value = 50
        param5.switch = InputSwitch.INT
        node_data.params.append(param5)

        param5 = FlowInputParam()
        param5.name = "top-p"
        param5.desc = "预测词累计概率阈值"
        param5.typeDef = "Float"
        param5.type = ParamType.float
        param5.require = True
        param5.value = 0.9
        param5.switch = InputSwitch.FLOAT
        node_data.params.append(param5)

        param5 = FlowInputParam()
        param5.name = "stop"
        param5.desc = "停止词,多个停止词之间使用空格隔开"
        param5.typeDef = "String"
        param5.type = ParamType.string
        param5.require = True
        param5.value = "<|im_end|>"
        param5.switch = InputSwitch.VALUE
        node_data.params.append(param5)
        #输出参数
        out1 = FlowOutputParam()
        out1.name = "output"
        out1.typeDef = "String"
        out1.desc = "模型输出结果"
        out1.type = ParamType.string
        node_data.returns.append(out1)
        #连接器
        return node_data
