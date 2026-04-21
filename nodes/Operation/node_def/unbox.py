from typing import Tuple, List, Any

from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputHandle, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

class UnBox(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError(f"context.content is not of type Content {context.label}")
        content: Content = context.content

        returnParam = ReturnParam()
        returnParam.is_finish = True
        try:
            if context.input_map["object"].value is None:
                await ws.send_json(WsMessageTool.error(context, "输入对象为None"))
                return ReturnParam()
            obj = context.input_map["object"].value
            for param_name, param_var in context.output_map.items():
                if isinstance(obj, dict):
                    value = obj.get(param_name, None)
                else:
                    value = getattr(obj, param_name, None)
                if value is not None:
                    param_var.value = value
                else:
                    param_var.value = UnBox.get_default_value(param_var.param_type)
                    await ws.send_json(WsMessageTool.error(context, f"对象中缺少参数:{param_name}"))
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))
        return returnParam

    @staticmethod
    def get_default_value(target_type: type) -> Any:
        """
        获取指定类型的默认空值

        参数:
            target_type: 目标类型

        返回:
            该类型的默认空值
        """
        if target_type == str:
            return ""
        elif target_type == int:
            return 0
        elif target_type == float:
            return 0.0
        elif target_type == bool:
            return False
        elif target_type == list:
            return []
        elif target_type == dict:
            return {}
        elif target_type == object:
            return object()
        else:
            return None

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
        node_data.type = "UNBOX"
        node_data.label = "对象解包"
        node_data.desc = "从对象中拿到参数\n支持从 object / dict[str,...] 对象中参数中取出与输出参数同名的参数\n如若字段存在则直接取出(不会检查类型或做类型转换)\n注:字段不存在或值为None的情况将初始化变量为对应类型的初始值并打印错误日志"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = True
        #输入参数
        param1 = FlowInputParam()
        param1.name = "object"
        param1.typeDef = "Object"
        param1.desc = "选择需要解包的对象"
        param1.type = ParamType.object
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)
        #输出参数
        #连接器
        return node_data
