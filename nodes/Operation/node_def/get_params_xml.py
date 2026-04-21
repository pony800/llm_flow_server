from pydantic import BaseModel, ConfigDict

from src.models.enums.vue_flow_enum import ParamType, InputSwitch
from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import FlowInputParam, NodeData, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
import re
import ast
from typing import List, Tuple, Any


class Content(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

class GetParamsXml(NodeInterface):
    @staticmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError("context.content is not of type Content")
        content:Content = context.content
        try:
            llmOutput = context.input_map["llmOutput"].value
            for key, item in context.output_map.items():
                pattern = re.compile(f'<{key}>(.*?)</{key}>', re.DOTALL)
                match = pattern.search(llmOutput)
                if not match:
                    # 没有找到匹配项，返回对应类型的空值
                    item.value = GetParamsXml.get_default_value(item.param_type)
                    continue
                extracted_value = match.group(1).strip()

                try:
                    # 尝试转换为指定类型
                    item.value = GetParamsXml.convert_value(extracted_value, item.param_type)
                except (ValueError, TypeError, SyntaxError):
                    # 转换失败，返回对应类型的空值
                    await ws.send_json(WsMessageTool.error(context, f"参数: '{key}' 尝试转换为{item.param_type}类型失败"))
                    item.value = GetParamsXml.get_default_value(item.param_type)
            pass
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))

        returnParam = ReturnParam()
        return returnParam

    @staticmethod
    def convert_value(value: str, target_type: type) -> Any:
        """
        将字符串值转换为目标类型

        参数:
            value: 要转换的字符串值
            target_type: 目标类型

        返回:
            转换后的值

        异常:
            如果转换失败会抛出ValueError, TypeError或SyntaxError
        """
        if target_type == str:
            return value
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == bool:
            # 处理布尔值转换
            if value.lower() in ('true', 'yes', '1'):
                return True
            elif value.lower() in ('false', 'no', '0'):
                return False
            raise ValueError(f"Cannot convert '{value}' to bool")
        elif target_type == list:
            # 使用ast.literal_eval安全地评估字符串表达式
            evaluated = ast.literal_eval(value)
            if not isinstance(evaluated, list):
                raise TypeError(f"Expected list, got {type(evaluated)}")
            return evaluated
        elif target_type == dict:
            evaluated = ast.literal_eval(value)
            if not isinstance(evaluated, dict):
                raise TypeError(f"Expected dict, got {type(evaluated)}")
            return evaluated
        else:
            raise TypeError(f"Unsupported type: {target_type}")

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
        # 基本信息
        node_data = NodeData()
        node_data.type = "GET_PARAMS_XML"
        node_data.label = "从模型输出中解析值(xml格式)"
        node_data.desc = "解析大模型回答中<参数名>值<//参数名>这样的结构并返回其值\n1.其中参数名来自于输出参数定义\n2.会尝试将值转换为输出参数定义的类型\n3.不支持多级嵌套,每个参数标签只能出现一次"
        node_data.content = Content()
        node_data.canAddParams = False
        node_data.canAddReturns = True
        # 输入参数
        param1 = FlowInputParam()
        param1.name = "llmOutput"
        param1.desc = "需要解析的字符串"
        param1.typeDef = "String"
        param1.type = ParamType.string
        param1.editable = False
        param1.require = True
        param1.switch = InputSwitch.PATH
        node_data.params.append(param1)
        # 输出参数
        # 连接器
        return node_data