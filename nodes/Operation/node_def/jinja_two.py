from typing import Tuple, List

from pydantic import BaseModel, ConfigDict
from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowOutputParam, FlowInputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
from jinja2 import Template

tempStr = """{# 一般多轮对话示例 #}
<|im_start|>system
你是一位人工智能助手,可以完成用户的交代的各项工作<|im_end|>
{# 历史记录循环 #}
{%- for history in historyList -%}
  {%- if history.role == 'user' %}
<|im_start|>user
{{ history.content }}<|im_end|>
  {%- elif history.role == 'assistant' %}
<|im_start|>assistant
{{ history.content }}<|im_end|>
  {%- else %}
<|im_start|>{{ history.role }}
{{ history.content }}<|im_end|>
  {%- endif -%}
{%- endfor -%}
{# 确保助手的响应位置 #}
<|im_start|>assistant"""

class Content(BaseModel):
    templateStr : str = ""
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Jinja2(NodeInterface):
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
            params : dict[str, object] = {}
            for key, value in context.input_map.items():
                params[key] = value.value
            template = Template(content.templateStr)
            context.output_map["prompt"].value = template.render(params)
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
        node_data.type = "JINJA2"
        node_data.label = "根据模板生成提示词"
        node_data.desc = "使用Jinja2库进行提示词拼接,请遵循jinja2语法\n1.提供模板快速编辑功能,具体使用可参考默认实例"
        node_data.content = Content()
        node_data.content.templateStr = tempStr
        node_data.canAddParams = True
        node_data.canAddReturns = False
        # 输入参数
        param1 = FlowInputParam()
        param1.name = "historyList"
        param1.type = ParamType.list
        param1.desc = "对话历史"
        param1.typeDef = "List<{role:string, content:string}>"
        param1.editable = True
        param1.require = True
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)
        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "prompt"
        out1.typeDef = "String"
        out1.desc = "输出生成的提示词"
        out1.type = ParamType.string
        out1.editable = False
        node_data.returns.append(out1)
        # 连接器
        return node_data