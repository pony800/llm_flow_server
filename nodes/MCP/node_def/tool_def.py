from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from nodes.MCP.croe.model import Function, AgentData, AgentType, FunParam
from src.core.common.constant import STOP_HANDLE_NAME, END_HANDLE_NAME
from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from enum import Enum

class Phase(str, Enum):
    WAIT = "wait"   #等待命令状态, 1.若命令为获取函数定义则直接返回当前函数定义 2.若命令为执行函数则解析调用参数放入返回中,并调用后续工具节点 next->RUN
    RUN = "run"     #后续工具节点已经执行结束, 从输参数这里获取后续节点执行结果拼装返回给agent客户端 next->null

class Content(BaseModel):
    phase: Phase = Phase.WAIT
    function_name: str = ""             #定义工具名称
    function_desc: str = ""             #工具描述
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ToolDef(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        returnParam = ReturnParam()

        try:
            agent_data: AgentData = context.input_map["agentData"].value
            if content.phase == Phase.WAIT:
                if agent_data.operation_type == AgentType.QUERY:
                    # 组装函数定义
                    agent_data.operation_type = AgentType.FUN_DEF
                    agent_data.function = Function()
                    agent_data.function.name = content.function_name
                    agent_data.function.desc = content.function_desc
                    #定义输出参数
                    for name, var in context.input_map.items():
                        if name is None or name == "agentData" or name == "status" or name == "message":
                            continue
                        else:
                            if var.param_def.type_def is None or var.param_def.type_def == "":
                                var.param_def.type_def = var.param_def.type.value
                            agent_data.function.returns.append(FunParam(name=name, type=var.param_def.type_def, desc=var.param_def.desc))
                    #定义输入参数
                    for name, var in context.output_map.items():
                        if name is None:
                            continue
                        else:
                            if var.param_def.type_def is None or var.param_def.type_def == "":
                                var.param_def.type_def = var.param_def.type.value
                            agent_data.function.params.append(FunParam(name=name, type=var.param_def.type_def, desc=var.param_def.desc))
                    returnParam.is_finish = True
                    returnParam.handler_name = STOP_HANDLE_NAME
                    return returnParam
                elif agent_data.operation_type == AgentType.EXEC:
                    #解析大模型调用参数并执行后续工具
                    # 将解析的参数填入输出参数中
                    for name, value in agent_data.params.items():
                        if name in context.output_map:
                            context.output_map[name].value = value
                    # 需要清空输入参数避免旧值干扰
                    for name, var in context.input_map.items():
                        if name is not None and name != "agentData":
                            var.value = None
                    content.phase = Phase.RUN
                    returnParam.is_finish = False
                    returnParam.handler_name = END_HANDLE_NAME
                    return returnParam
            elif content.phase == Phase.RUN:
                #解析并拼装工具返回结果
                agent_data.params.clear()
                for name, var in context.input_map.items():
                    if name is None or name == "agentData" or name == "status" or name == "message":
                        continue
                    else:
                        agent_data.params[name] = var.value
                #封装放回结果
                agent_data.operation_type = AgentType.RETURN
                if not context.input_map["status"].value:
                    agent_data.status = False
                else:
                    agent_data.status = True
                agent_data.message = context.input_map["message"].value

                content.phase = Phase.WAIT
                returnParam.is_finish = True
                returnParam.handler_name = STOP_HANDLE_NAME
                return returnParam
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))

        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        content.phase = Phase.WAIT
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "TOOL_DEF"
        node_data.label = "工具定义节点"
        node_data.desc = "定义大模型使用的工具(可以将后方的流程封装为一个工具)\n1.定义工具的返回值:添加输入参数并选择后续流程的返回值作为工具的返回值\n2.定义工具的入参:添加输出参数并在后续流程中使用\n3.请为定义的入参和返回值编写注释定义其类型和作用(编写的格式可参考其他节点默认参数)\n4.首次运行到MCP客户端时会将工具定义(工具名称,描述,参数定义等)一并注入到提示词中"
        node_data.content = Content()
        node_data.canAddParams = True
        node_data.canAddReturns = True
        node_data.switch = InputSwitch.REPATH
        # 输入参数
        param1 = FlowInputParam()
        param1.name = "agentData"
        param1.desc = "请选择Agent客户端"
        param1.type = "McpData"
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "status"
        param2.desc = "请绑定工具执行结果"
        param2.type = ParamType.bool
        param2.editable = False
        param2.require = True
        param2.switch = InputSwitch.REPATH
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "message"
        param3.desc = "请绑定 错误说明|执行结果说明"
        param3.type = ParamType.string
        param3.editable = False
        param3.require = False
        param3.switch = InputSwitch.REPATH
        node_data.params.append(param3)

        # 连接器
        return node_data