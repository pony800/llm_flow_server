from typing import Tuple, TextIO

from pydantic import BaseModel, ConfigDict
from itertools import islice
from typing import Optional, List, Pattern
from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam, FlowOutputHandle

from src.core.common.config_manager import DATA_PATH
from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Content(BaseModel):
    processing_file: TextIO | None = None
    delimiter_pattern: Optional[Pattern] = None
    current_line: int = 0
    remaining: str = ""
    delimiters: list[str] = []
    contains_newline: bool = False
    count: int = 0
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ForTxt(NodeInterface):
    """
    输入参数:
        txt         [str]                   :选择的文件路径
        separators  [str]                   :分隔符
    输出参数:
        currentLine [int]                   :当前循环
        currentText [str]                   :当前文本串
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
            if not content.processing_file:
                content.processing_file = open(DATA_PATH / context.input_map["txt"].value, "r", encoding='utf-8')
                content.delimiters = context.input_map["separators"].value.split()
                content.current_line = context.input_map["startLine"].value
                content.remaining = ""
                content.contains_newline = '\n' in context.input_map["separators"].value
                content.count = 0
                if "\\n" in context.input_map["separators"].value:
                    content.delimiters.append("\n")
                if content.current_line > 0:
                    next(islice(content.processing_file, content.current_line - 1, None), None)
            # 处理剩余内容
            while True:
                # 优先检查剩余内容
                if content.remaining:
                    # 找出最早出现的分隔符位置
                    positions = []
                    for sep in content.delimiters:
                        if sep in content.remaining:
                            pos = content.remaining.index(sep)
                            positions.append((pos, sep))

                    if positions:
                        # 按出现位置排序
                        positions.sort()
                        first_pos, first_sep = positions[0]

                        # 分割内容
                        token = content.remaining[:first_pos]
                        content.remaining = content.remaining[first_pos + len(first_sep):]
                        context.output_map["currentText"].value = token
                        context.output_map["currentLine"].value = content.current_line
                        context.output_map["count"].value = content.count
                        content.count += 1
                        returnParam.is_finish = False
                        returnParam.handler_name = "for"
                        break

                # 读取新行
                line = next(islice(content.processing_file, 0, None), None)
                if line is None:  # 文件结束
                    content.processing_file.close()
                    if not content.remaining:
                        context.output_map["currentText"].value = ""
                        context.output_map["currentLine"].value = content.current_line
                        context.output_map["count"].value = content.count
                        content.count += 1
                        returnParam.is_finish = True
                        content.processing_file = None
                        break
                    token = content.remaining
                    content.remaining = ""
                    context.output_map["currentText"].value = token
                    context.output_map["currentLine"].value = content.current_line
                    context.output_map["count"].value = content.count
                    content.count += 1
                    returnParam.is_finish = False
                    returnParam.handler_name = "for"
                    break

                content.current_line += 1

                # 如果分隔符不包含换行符，保留原始换行符
                if not content.contains_newline:
                    line = line.rstrip('\n') + '\n'

                # 合并剩余内容
                content.remaining += line
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
        node_data.type = "FOR_TXT"
        node_data.label = "文本文件迭代器"
        node_data.desc = "读取文本文件并按照规则切分文件返回每一个片段\n1.支持多种分割符混用,如'\\n break next b'使用空格将多个分割字符串隔开使其同生效\n2.内部算法将逐行读取文件拼接后进行切分并返回,支持读取超大文件不会发生内存溢出\n注:当循环执行完成后会继续执行与结束连接器相连的节点"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = False
        # 输入参数
        param1 = FlowInputParam()
        param1.name = "txt"
        param1.path = []
        param1.desc = "请选择需要遍历处理的文本文件"
        param1.type = "txt"
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.FILE
        node_data.params.append(param1)

        param2 = FlowInputParam()
        param2.name = "separators"
        param2.type = ParamType.string
        param2.value = "\\n"
        param2.desc = "文本分隔符, 支持多个(使用' '隔开)"
        param2.editable = False
        param2.require = True
        param2.switch = InputSwitch.VALUE
        node_data.params.append(param2)

        param3 = FlowInputParam()
        param3.name = "startLine"
        param3.desc = "跳过前面的行从这一行开始迭代"
        param3.type = ParamType.int
        param3.value = 0
        param3.editable = False
        param3.require = True
        param3.switch = InputSwitch.INT
        node_data.params.append(param3)
        # 输出参数
        out1 = FlowOutputParam()
        out1.name = "currentText"
        out1.desc = "当前切分文本片段"
        out1.type = ParamType.string
        out1.editable = False
        node_data.returns.append(out1)

        out2 = FlowOutputParam()
        out2.name = "currentLine"
        out2.desc = "当前处理到第几行"
        out2.type = ParamType.int
        out2.editable = False
        node_data.returns.append(out2)

        out3 = FlowOutputParam()
        out3.name = "count"
        out3.desc = "当前循环第几次"
        out3.type = ParamType.int
        out3.editable = False
        node_data.returns.append(out3)
        # 连接器
        handle1 = FlowOutputHandle()
        handle1.name = "for"
        handle1.label = "切分循环"
        node_data.handles.append(handle1)
        return node_data