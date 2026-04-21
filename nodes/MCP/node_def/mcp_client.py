from typing import List, Iterator, Tuple

from pydantic import BaseModel, ConfigDict

from nodes.MCP.croe.model import Plan, Dialogue, Function, AgentData, AgentType, DialogueExec
from nodes.MCP.croe.const_data import qwen_mcp_prompt, query_stdio_content, operate_stdio_content
from nodes.MCP.croe.parse_result_container import ParseResultContainer, Operation, OperationType
from src.core.common.constant import END_HANDLE_NAME, STOP_HANDLE_NAME
from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam, OutputHandler
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam, FlowOutputHandle

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from enum import Enum
from jinja2 import Template
import json

END_HANDLE = OutputHandler()

class Phase(str, Enum):
    INIT = "init"           # 进行初始化行动
    QUERY = "query"         # 进行agent初始化操作(只执行一次) 1.遍历所有的handler确定有哪些可调用工具 未结束遍历 next->START 结束遍历 next->generate
    FUN_DEF = "fun_def"     # 解析函数定义节点返回的函数定义 next->QUERY
    GENERATE = "generate"   # 数据已经准备完成调用大模型进行输出 1.使用模板引擎生成完整提示词 2.调用大模型进行输出 next->ANALYSIS
    ANALYSIS = "analysis"   # 获取大模型输出结果并开始解析执行 1.解析LLM输出结果放入current_result中 next->EXECUTE
    EXECUTE = "execute"     # 顺序执行current_result中的操作并构建返回结果更新历史记录 若还有操作继续执行 next->EXECUTE 若没有结束标签且没有超出轮次上限 next->GENERATE 否则 next->END
    RETURN = "return"       # 解析工具调用结果并整理结果 next->EXECUTE
    END = "end"             # 结束执行返回 is_finish = True

class Content(BaseModel):
    max_step: int = 10   # 计划轮次上限
    phase: Phase = Phase.QUERY
    current_result: ParseResultContainer|None = None  # 当前大模型回答解析内容

    current_operation: Operation|None = None   # 当前执行的操作
    current_handler_name: str | None = None
    func_handle_iter: Iterator[str]|None = None
    bool_pass: bool = False # 是否跳过后续步骤

    #----提示词模板数据----#
    function_map: dict[str, Function] = dict() # dict[function_name, function]
    plan_history: List[Plan] = []    # 执行历史记录
    dialogue_history: List[Dialogue] = []   # 对话历史
    result_list: List[DialogueExec] = []    # 本轮计划执行结果列表
    prompt: str = qwen_mcp_prompt

    model_config = ConfigDict(arbitrary_types_allowed=True)

class McpClient(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        returnParam = ReturnParam()
        try:
            agent_data:AgentData = context.output_map["agentData"].value
            if content.phase == Phase.QUERY:
                # 查询接下来一个连接器的函数定义
                handler_name:str = next(content.func_handle_iter,END_HANDLE)
                returnParam.handler_name = STOP_HANDLE_NAME
                if handler_name is END_HANDLE:
                    # 函数获取遍历结束进入下一阶段生成
                    content.phase = Phase.GENERATE
                    content.func_handle_iter = None
                elif handler_name == END_HANDLE_NAME or handler_name == "llm":
                    # 跳过完成连接器和大语言模型连接器
                    pass
                else:
                    # 查询函数定义器返回结果
                    context.output_map["agentData"].value = AgentData(operation_type=AgentType.QUERY)
                    content.current_handler_name = handler_name
                    content.phase = Phase.FUN_DEF
                    returnParam.handler_name = handler_name
                returnParam.is_finish = False
                return returnParam
            elif content.phase == Phase.FUN_DEF:
                # 解析连接器返回的函数定义
                if agent_data.operation_type != AgentType.FUN_DEF:
                    await ws.send_json(WsMessageTool.error(context,
                    f"连接器: {content.current_handler_name} 未正确返回函数定义"))
                else:
                    try:
                        agent_data.function.handle_name = content.current_handler_name
                        content.function_map[agent_data.function.name] = agent_data.function
                    except Exception as e:
                        await ws.send_json(WsMessageTool.error(context,
                        f"连接器: {content.current_handler_name} 解析函数定义失败,原因:{str(e)}"))
                content.phase = Phase.QUERY
                returnParam.is_finish = False
                returnParam.handler_name = STOP_HANDLE_NAME
                return returnParam
            elif content.phase == Phase.GENERATE:
                # 填入构建模板参数
                response = ""
                for result in content.result_list:
                    response += result.step_id + ":" + "status=" + result.status
                    if result.returns and result.returns != "\"\"":
                        response += ",returns=" + result.returns
                    if result.status == "success" and result.response:
                        response += ",response=\"" + result.response + "\""
                    elif result.status == "fail" and result.response:
                        response += ",message=\"" + result.response + "\""
                    response += ";\n"
                response = response.rstrip('\n')
                content.result_list.clear()
                if response != "":
                    content.dialogue_history.append(Dialogue(role="user", content=response))
                if len(content.dialogue_history) > 3:
                    del content.dialogue_history[:2]
                params: dict[str, object] = {
                    "function_map": content.function_map,
                    "plan_history": content.plan_history,
                    "dialogue_history": content.dialogue_history,
                    "mission": context.input_map["mission"].value
                }
                template = Template(content.prompt)
                context.output_map["prompt"].value = template.render(params)
                # 调用大模型生成
                content.phase = Phase.ANALYSIS
                returnParam.is_finish = False
                returnParam.handler_name = "llm"
                return returnParam
            elif content.phase == Phase.ANALYSIS:
                # 重置中间变量
                content.result_list = []
                content.bool_pass = False
                # 解析大模型返回参数
                output = context.input_map["llmOutput"].value
                if output is None or output == "":
                    await ws.send_json(WsMessageTool.error(context, "大语言模型未能正确输出内容,请检查原因"))
                    returnParam.is_finish = True
                    returnParam.handler_name = STOP_HANDLE_NAME
                    return returnParam
                # 将模型输出加入对话历史
                content.dialogue_history.append(Dialogue(role="assistant", content=output))
                # 解析回答结果
                content.current_result.parse_mcp_output(output)
                # 检查输出是否正常
                if content.current_result.check_out():
                    content.dialogue_history.append(Dialogue(role="user", content="注意:请按照给定的模板进行有效回答"))
                    await ws.send_json(WsMessageTool.error(context, "大语言模型未输出任何可执行内容,请检查原因"))
                # 切换到执行模式
                content.phase = Phase.EXECUTE
                returnParam.is_finish = False
                returnParam.handler_name = STOP_HANDLE_NAME
                return returnParam
            elif content.phase == Phase.EXECUTE:
                # 按步骤顺序执行大模型返回的计划
                returnParam.is_finish = False
                returnParam.handler_name = STOP_HANDLE_NAME
                if not content.current_result.operations:
                    if content.current_result.is_success is None:
                        content.phase = Phase.GENERATE
                        return returnParam
                    elif content.current_result.is_success is not None:
                        content.phase = Phase.END
                        return returnParam
                step, content.current_operation = content.current_result.pop_operation()
                if content.bool_pass:
                    # 如果有计划执行返回失败则将该轮后续计划全部标记为跳过
                    McpClient.record_write(content, AgentData(operation_type=AgentType.RETURN, status=False))
                    return returnParam
                elif content.current_operation.type == OperationType.TOOL:
                    # 封装参数调用函数
                    if content.current_operation.operation not in content.function_map:
                        # 大模型调用不存在的函数
                        McpClient.record_write(content, AgentData(operation_type=AgentType.RETURN,status=False,message="调用的函数不存在"))
                    else:
                        # 发起工具调用
                        current_function = content.function_map[content.current_operation.operation]
                        returnParam.handler_name = current_function.handle_name
                        agent_data = AgentData(operation_type=AgentType.EXEC)
                        agent_data.call_name = current_function.name
                        agent_data.params = content.current_operation.params
                        context.output_map["agentData"].value = agent_data
                        content.phase = Phase.RETURN
                elif content.current_operation.type == OperationType.QUERY:
                    # 切换标准输入输出的询问界面并询问用户问题
                    await ws.send_json(WsMessageTool.set_content(context, "STDIO", query_stdio_content))
                    await ws.send_json(WsMessageTool.put_values(context, {"#query":content.current_operation.operation, "#status":False}))
                    await ws.send_json(WsMessageTool.get_values(context, ["#response","#status"]))
                    return_json = await ws.receive_json()
                    McpClient.record_write(content, AgentData(operation_type=AgentType.RETURN, status=return_json["#status"],
                                                              message=return_json["#response"]))
                    returnParam.handler_name = STOP_HANDLE_NAME
                elif content.current_operation.type == OperationType.OPERATE:
                    # 切换标准输入输出的询问界面并询户执行操作结果
                    await ws.send_json(WsMessageTool.set_content(context, "STDIO", operate_stdio_content))
                    await ws.send_json(
                        WsMessageTool.put_values(context, {"#operate": content.current_operation.operation}))
                    await ws.send_json(WsMessageTool.get_values(context, ["#response", "#status"]))
                    return_json = await ws.receive_json()
                    McpClient.record_write(content,
                                           AgentData(operation_type=AgentType.RETURN, status=return_json["#status"],
                                                     message=return_json["#response"]))
                    returnParam.handler_name = STOP_HANDLE_NAME

                returnParam.is_finish = False
                return returnParam
            elif content.phase == Phase.RETURN:
                # 解析工具返回结果维护到结果对象内
                current_function = content.function_map[content.current_operation.operation]
                if agent_data.operation_type != AgentType.RETURN:
                    McpClient.record_write(content, AgentData(operation_type=AgentType.RETURN, status=False,
                                                              message="函数调用失败"))
                    await ws.send_json(WsMessageTool.error(context,
                    f"连接器:{current_function.handle_name} 调用函数:{current_function.name}失败, 参数:{content.current_operation.params}"))
                McpClient.record_write(content, agent_data)
                content.phase = Phase.EXECUTE
                returnParam.is_finish = False
                returnParam.handler_name = STOP_HANDLE_NAME
                return returnParam
            elif content.phase == Phase.END:
                context.output_map["isSuccess"].value = content.current_result.is_success
                context.output_map["message"].value = content.current_result.message
                returnParam.is_finish = True
                returnParam.handler_name = END_HANDLE_NAME
            elif content.phase == Phase.INIT:
                # 1.初始化模型结果解析对象
                content.current_result = ParseResultContainer()
                # 2.初始化函数轮询迭代器
                content.func_handle_iter = iter(context.handler_map)
                content.phase = Phase.QUERY
                returnParam.is_finish = False
                returnParam.handler_name = STOP_HANDLE_NAME
                return returnParam
        except Exception as e:
            returnParam.is_finish = True
            await ws.send_json(WsMessageTool.error(context, str(e)))

        return returnParam

    @staticmethod
    def record_write(content:Content, agent_data:AgentData):
        if content.bool_pass:
            status = "pass"
            returns=None
            response=None
            is_success=False
        elif agent_data.status:
            status = "success"
            returns = json.dumps(agent_data.params, separators=(',', ':'), ensure_ascii=False)
            response = agent_data.message
            is_success = True
        else:
            status = "fail"
            returns = json.dumps(agent_data.params, separators=(',', ':'), ensure_ascii=False)
            response = agent_data.message
            is_success = False
        if returns == "\"\"":
            returns = None

        content.plan_history.append(
            Plan(exec_str=content.current_operation.exec_str,
                 is_success=is_success,
                 returns=returns,
                 response=response))
        content.result_list.append(
            DialogueExec(step_id=content.current_operation.step_id,
                         status=status,
                         returns=returns,
                         response=response))
        if not agent_data.status:
            # 如果函数执行失败则跳过后续步骤的执行
            content.bool_pass = True

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)
        content.phase = Phase.INIT
        content.function_map = dict()  # dict[function_name, function]
        content.plan_history = []  # 执行历史记录
        content.dialogue_history = []  # 对话历史
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "MCP_CLIENT"
        node_data.label = "Mcp客户端"
        node_data.desc = "针对小模型开发的函数调用执行工具,让小模型拥有简单的工具调用能力\n1.可以直接将任何一段搭建的流程定义为工具供大模型进行调用\n2.对于每一个连接的工具定义节点其会在首次运行时自动获取其工具定义并注入到模型的提示词中\n3.实现方式针对小模型进行优化(包括函数定义方式,计划记录等等)降低模型困惑度和对长上下文的依赖\n4.默认为模型提供'询问用户'和'让用户代为执行'两个能力(如若不需要可以编辑提示词来去掉这一能力)\n5.具体实现细节可参照其提示词模板"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        # 输入参数
        param1 = FlowInputParam()
        param1.name = "mission"
        param1.desc = "需要解决的最终任务"
        param1.type = ParamType.string
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "llmOutput"
        param2.desc = "该参数连接后续大模型的输出"
        param2.type = ParamType.string
        param2.editable = False
        param2.require = True
        param2.switch = InputSwitch.REPATH
        node_data.params.append(param2)

        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "agentData"
        out1.type = "McpData"
        out1.desc = "agent输出参数"
        out1.editable = False
        node_data.returns.append(out1)

        out2 = FlowOutputParam()
        out2.name = "prompt"
        out2.type = ParamType.string
        out2.desc = "大模型提示词,请将其填入llm节点的提示词参数"
        out2.editable = False
        node_data.returns.append(out2)

        out3 = FlowOutputParam()
        out3.name = "planList"
        out3.type = ParamType.list
        out3.typeDef = "List[Plan], Plan={exec_str: str(模型调用字符串), is_success: bool(是否执行成功), returns: str(返回结果), response: str}"
        out3.desc = "执行成功的计划列表"
        out3.editable = False
        node_data.returns.append(out3)

        out4 = FlowOutputParam()
        out4.name = "isSuccess"
        out4.type = ParamType.bool
        out4.desc = "任务是否成功完成"
        out4.editable = False
        node_data.returns.append(out4)

        out5 = FlowOutputParam()
        out5.name = "message"
        out5.type = ParamType.string
        out5.desc = "任务完成说明"
        out5.editable = False
        node_data.returns.append(out5)
        # 连接器
        handle1 = FlowOutputHandle()
        handle1.name = "llm"
        handle1.label = "LLM"
        node_data.handles.append(handle1)
        return node_data