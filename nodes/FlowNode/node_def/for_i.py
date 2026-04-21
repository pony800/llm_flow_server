from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputHandle, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    #内部计数器
    step: int = 1
    #记录是否为初始状态(未开始状态)初始值为True
    init: bool = True
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ForI(NodeInterface):
    """
    输入参数:
        startWith   [int]   :从这里开始循环(计数器初始值)
        endWith     [int]   :当计数器大于等于endWith时结束循环
    输出参数:
        current     [int]   :当前循环计数器值
    连接器:
        for                 :当需要继续循环时激活该连接器,否则激活默认连接器
    """
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError(f"context.content is not of type Content {context.label}")
        content: Content = context.content

        returnParam = ReturnParam()
        if content.init:
            content.init = False
            context.output_map["current"].value = context.input_map["startWith"].value
            content.step = context.input_map["step"].value
            if content.step == 0:
                await ws.send_json(WsMessageTool.error(context, "步长不能为0"))
                content.step = 1
            if content.step < 0:
                await ws.send_json(WsMessageTool.error(context, "步长不能为负数"))
                content.step = -content.step
            returnParam.is_finish = False
            returnParam.handler_name = "for"
            return returnParam
        try:
            current = context.output_map["current"].value
            if context.input_map["endWith"].value > context.input_map["startWith"].value:
                if current >= context.input_map["endWith"].value:
                    content.init = True
                current += content.step
            else:
                if current <= context.input_map["endWith"].value:
                    content.init = True
                current -= content.step
            if content.init:
                returnParam.is_finish = True
            else:
                returnParam.is_finish = False
                returnParam.handler_name = "for"
            context.output_map["current"].value = current
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))
        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        content.init = True
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        #基本信息
        node_data = NodeData()
        node_data.type = "FOR_I"
        node_data.label = "从I到J循环"
        node_data.desc = "将从startWith(包含)开始每次循环输出+1直到endWith(包含)为止\n注:会自动根据startWith和endWith的大小来进行自增循环或自减循环\n注:当循环执行完成后会继续执行与结束连接器相连的节点"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        #输入参数
        param1 = FlowInputParam()
        param1.name = "startWith"
        param1.typeDef = "Integer"
        param1.desc = "从此处开始循环(包含此值)"
        param1.type = ParamType.int
        param1.editable = False
        param1.require = True
        param1.value = 0
        param1.switch = InputSwitch.INT
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "endWith"
        param2.typeDef = "Integer"
        param2.desc = "循环至此(包含此值)"
        param2.type = ParamType.int
        param2.editable = False
        param2.require = True
        param2.value = 10
        param2.switch = InputSwitch.INT
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "step"
        param3.typeDef = "Integer"
        param3.desc = "步长(每次循环会增加或减少的值,不可以为负数)"
        param3.type = ParamType.int
        param3.editable = False
        param3.require = True
        param3.value = 1
        param3.switch = InputSwitch.INT
        node_data.params.append(param3)
        #输出参数
        out1 = FlowOutputParam()
        out1.name = "current"
        out1.desc = "当前循环的值(该值支持被后续节点修改)"
        out1.typeDef = "Integer"
        out1.type = ParamType.int
        out1.editable = False
        node_data.returns.append(out1)
        #连接器
        handle1 = FlowOutputHandle()
        handle1.name = "for"
        handle1.label = "for循环"
        node_data.handles.append(handle1)
        return node_data
