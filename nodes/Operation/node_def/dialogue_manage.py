from typing import Tuple, List

from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowOutputParam, FlowInputParam, FlowOutputHandle

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from jinja2 import Template

class DialogueModel(BaseModel):
    role: str
    content: str

class Content(BaseModel):
    current_role : str|None = None
    count: int = 0
    model_config = ConfigDict(arbitrary_types_allowed=True)

class DialogueManage(NodeInterface):
    """
        输入参数:
            historyList     [list]
        输出参数:
            prompt          [string]   :拼接后的提示词
        连接器:
        """
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        returnParam = ReturnParam()

        try:
            history_list = context.output_map["historyList"].value
            if content.current_role is None:
                # 第一次进入, 初始化
                addList = context.input_map["historyList"].value
                # 如果有初始数据则加入
                if addList is not None:
                    for item in addList:
                        history_list.append(item)
                firstMove = context.input_map["firstMove"].value
                content.count = 0
                if firstMove == "LLM":
                    content.current_role = "assistant"
                    returnParam.handler_name = "llm"
                elif firstMove == "USER":
                    content.current_role = "user"
                    returnParam.handler_name = "user"
                else:
                    await ws.send_json(WsMessageTool.error(context, f"枚举参数 firstMove:{firstMove} 取值非法"))
                    returnParam.is_finish = True
                    return returnParam
            else:
                content.count += 1
                context.output_map["count"].value = content.count
                if content.current_role == "assistant":
                    output = context.input_map["llmOutput"].value
                    if output == context.input_map["endWith"].value:
                        content.current_role = None
                        returnParam.is_finish = True
                        return returnParam
                    # 上一次类型为assistant
                    history_list.append(DialogueModel(role="assistant", content=output))
                    context.output_map["lastRecord"].value = output
                    content.current_role = "user"
                    returnParam.handler_name = "user"
                elif content.current_role == "user":
                    output = context.input_map["userOutput"].value
                    if output == context.input_map["endWith"].value:
                        content.current_role = None
                        returnParam.is_finish = True
                        return returnParam
                    # 上一次类型为user
                    history_list.append(DialogueModel(role="user", content=output))
                    context.output_map["lastRecord"].value = output
                    content.current_role = "assistant"
                    returnParam.handler_name = "llm"
                if len(history_list) > context.input_map["length"].value:
                    history_list.pop(0)
            returnParam.is_finish = False
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
        return content, []

    @staticmethod
    def get_init_node_data() -> NodeData:
        # 基本信息
        node_data = NodeData()
        node_data.type = "DIALOGUE_MANAGE"
        node_data.label = "对话记录管理"
        node_data.desc = "内部维护对话历史记录列表\n1.会循环调用 LLM 连接器和 USER 连接器并将返回内容按角色插入到对话历史中\n2.任意连接器输出退出字符后结束循环(结束后historyList会被保留作为下次进入时的初始值)\n3.可以直接修改其输出参数historyList中的值来改变历史对话内容"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False

        # 输入参数
        param1 = FlowInputParam()
        param1.name = "firstMove"
        param1.typeDef = "LLM / USER"
        param1.desc = "选择循环从哪里开始(语言模型/用户输入)"
        param1.type = ParamType.enum
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.SELECT
        param1.selectList = ["LLM", "USER"]
        param1.value = "USER"
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "llmOutput"
        param2.typeDef = "String"
        param2.desc = "需要被记录的大模型输出内容"
        param2.type = ParamType.string
        param2.editable = False
        param2.require = True
        param2.switch = InputSwitch.REPATH
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "userOutput"
        param3.typeDef = "String"
        param3.desc = "需要被记录的用户输入"
        param3.type = ParamType.string
        param3.editable = False
        param3.require = True
        param3.switch = InputSwitch.REPATH
        node_data.params.append(param3)

        param4 = FlowInputParam()
        param4.name = "length"
        param4.typeDef = "String"
        param4.desc = "记录对话的数量(插入新数据时若超出长度则删除最前面一条数据)"
        param4.type = ParamType.int
        param4.editable = False
        param4.require = True
        param4.value = 20
        param4.switch = InputSwitch.INT
        node_data.params.append(param4)

        param5 = FlowInputParam()
        param5.name = "endWith"
        param5.typeDef = "String"
        param5.desc = "当收到此字符串时结束对话"
        param5.type = ParamType.string
        param5.editable = False
        param5.require = False
        param5.value = "end"
        param5.switch = InputSwitch.VALUE
        node_data.params.append(param5)

        param6 = FlowInputParam()
        param6.name = "historyList"
        param6.typeDef = "List<{role:string, content:string}>"
        param6.desc = "历史对话初始内容,如果传入则会被添加到初始对话中(不会改变传入列表的内容)"
        param6.type = ParamType.list
        param6.editable = False
        param6.require = False
        param6.switch = InputSwitch.PATH
        node_data.params.append(param6)

        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "historyList"
        out1.type = ParamType.list
        out1.typeDef = "List<{role:string, content:string}>"
        out1.desc = "对话历史列表, role:角色 user/assistant"
        out1.editable = False
        node_data.returns.append(out1)

        out2 = FlowOutputParam()
        out2.name = "lastRecord"
        out2.type = ParamType.string
        out2.typeDef = "String"
        out2.desc = "最后一条对话记录,若调用LLM连接器则值为用户最后输入,若调用USER连接器则值为大模型最后输出"
        out2.editable = False
        node_data.returns.append(out2)

        out3 = FlowOutputParam()
        out3.name = "count"
        out3.type = ParamType.int
        out3.typeDef = "Integer"
        out3.desc = "对话次数"
        out3.editable = False
        node_data.returns.append(out3)

        # 连接器
        handle1 = FlowOutputHandle()
        handle1.name = "llm"
        handle1.label = "LLM"
        node_data.handles.append(handle1)

        handle2 = FlowOutputHandle()
        handle2.name = "user"
        handle2.label = "USER"
        node_data.handles.append(handle2)
        return node_data