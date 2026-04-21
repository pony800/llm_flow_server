from enum import Enum
from types import CodeType
from typing import Tuple, List

from pydantic import BaseModel, ConfigDict
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool

class Phase(str, Enum):
    INIT = "init"
    RETURN = "return"

class Content(BaseModel):
    conditionMap: dict[str, str | CodeType] = dict() #条件代码 dict[handle.name, code]
    phase: Phase = Phase.INIT
    model_config = ConfigDict(arbitrary_types_allowed=True)

class IfElse(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        returnParam = ReturnParam()

        try:
            if content.phase == Phase.RETURN:
                # 第二次进入直接结束
                content.phase = Phase.INIT
                returnParam.is_finish = True
                return returnParam
            elif content.phase == Phase.INIT:
                # 首次进入进行条件判断
                content.phase = Phase.RETURN
                env = dict()
                #执行代码 从头开始遍历条件节点找到第一个满足条件的节点并返回连接器
                for param_name, var in context.input_map.items():
                    env[param_name] = var.value
                for handle_name, code in content.conditionMap.items():
                    if eval(code, env):
                        returnParam.is_finish = False
                        returnParam.handler_name = handle_name
                        return returnParam
                else:
                    returnParam.is_finish = False
                    returnParam.handler_name = "#else"
                    return returnParam
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))

        #异常情况
        returnParam.is_finish = True
        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        content.phase = Phase.INIT
        messages:List[str] = []
        if content.conditionMap is None:
            messages.append("条件为空")
        for handle_name, code in content.conditionMap.items():
            try:
                content.conditionMap[handle_name] = compile(code, '<string>', 'eval')
            except Exception as e:
                messages.append(f"条件:'{code}'编译失败(连接器:'{handle_name}')原因:{str(e)}")
        return content, messages

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "IF_ELSE"
        node_data.label = "根据不同条件选择不同分支"
        node_data.desc = "1.按照添加条件的顺序进行判断,并进入第一个返回True的分支\n2.如果没有任何分支返回True则进入else节点\n注:当分支执行完成后会继续执行与结束连接器相连的节点"
        node_data.content = Content()
        node_data.canAddParams = True
        # 输入参数
        # 输出参数
        # 连接器
        return node_data