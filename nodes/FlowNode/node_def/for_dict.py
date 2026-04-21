from typing import Iterator, Tuple, List

from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam, FlowOutputHandle

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    iterator: Iterator[Tuple[object, object]] | None = None
    count: int = 0
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ForDict(NodeInterface):
    """
    输入参数:
        dictData    [dict[object,object]]   :当计数器大于等于endWith时结束循环
    输出参数:
        key         [object]                :当前循key值
        value       [object]                :当前循value值
    连接器:
        for                                 :当需要继续循环时激活该连接器,否则激活默认连接器
    """
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        returnParam = ReturnParam()
        try:
            if not content.iterator:
                content.iterator = iter(context.input_map["dictData"].value.items())
                content.count = 0
            try:
                key, value = next(content.iterator)  # 获取下一个元素
                #正确拿到下一个值
                context.output_map["key"].value = key
                context.output_map["value"].value = value
                context.output_map["count"].value = content.count
                content.count += 1
                returnParam.is_finish = False
                returnParam.handler_name = "for"
            except StopIteration:  # 捕获迭代结束异常
                #迭代结束
                content.iterator = None
                returnParam.is_finish = True
                return returnParam
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
        node_data.type = "FOR_DICT"
        node_data.label = "迭代器循环字典"
        node_data.desc = "迭代字典对象,并返回字典的key和value\n注:当循环执行完成后会继续执行与结束连接器相连的节点"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        # 输入参数
        param1 = FlowInputParam()
        param1.name = "dictData"
        param1.type = ParamType.dict
        param1.typeDef = "Dict<Object, Object>"
        param1.desc = "选择需要遍历的字典对象(确保传入的对象不为None)"
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)
        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "key"
        out1.typeDef = "Object"
        out1.desc = "当前遍历的item的key值"
        out1.type = ParamType.object
        out1.editable = False
        node_data.returns.append(out1)

        out2 = FlowOutputParam()
        out2.name = "value"
        out2.typeDef = "Object"
        out2.desc = "当前遍历的item的value值"
        out2.type = ParamType.object
        out2.editable = False
        node_data.returns.append(out2)

        out3 = FlowOutputParam()
        out3.name = "count"
        out3.typeDef = "Integer"
        out3.desc = "迭代计数器(从0开始)"
        out3.type = ParamType.int
        out3.editable = False
        node_data.returns.append(out3)
        # 连接器
        handle1 = FlowOutputHandle()
        handle1.name = "for"
        handle1.label = "for循环"
        node_data.handles.append(handle1)
        return node_data