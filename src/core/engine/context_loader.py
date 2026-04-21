from collections import defaultdict
from typing import List

from src.models.computation.context import FullContext, Edge, OutputHandler
from src.models.computation.vue_flow import FlowContext
from src.tools.progress_tools import get_edge_key
from src.core.common.config_manager import PROJECT_PATH
from src.core.common.constant import PROGRESS_NODE_TYPE, END_HANDLE_NAME, PARENT_NODE_ID, START_NODE_ID, \
    OFF_LINE_NODE_TYPE
from src.models.enums.vue_flow_enum import InputSwitch, ParamType
from src.models.computation.context import NodeContext, Var, Param
import json
import os

class ContextLoader:
    def __init__(self, node_dict:dict):
        self._node_dict:dict = node_dict
        self._file_path_list:list[str] = []
        self._opened_file: dict[str, str] = {}
        self.is_success: bool = True
        self.error_messages: dict[str, dict[str, dict[str, List[str]]]] = {}

    def loader_new_context(self, file_path:str) -> NodeContext:
        #加载新流程的时候文件路径列表需清空
        self._file_path_list: list[str] = []
        return self._init_context(file_path)

    def _read_json_file(self, file_path:str) -> str:
        try:
            # 检查循环调用
            if file_path in self._file_path_list:
                self._add_exception_static("循环引用错误" ,f"{file_path}流程存在循环引用", None)
                return ""
            self._file_path_list.append(file_path)
            #如果是已经打开过的历史文件直接返回
            if file_path in self._opened_file:
                return self._opened_file[file_path]
            #打开新文件
            file = os.path.join(PROJECT_PATH / file_path)
            with open(file, "r", encoding='utf-8') as file:
                json_str = json.load(file)
                self._opened_file[file_path] = json_str
                return json_str
        except Exception:
            self._add_exception_static("流程文件打开失败", f"读取文件{PROJECT_PATH / file_path}失败", None)
            return ""

    def _close_json_file(self, file_path):
        if self._file_path_list.pop() != file_path:
            raise Exception(f"打开关闭文件{PROJECT_PATH / file_path}顺序异常")

    @staticmethod
    def _get_param_type(param_type: ParamType | str):
        if isinstance(param_type, str):
            try:
                return ParamType(param_type)
            except ValueError:
                return param_type
        return param_type

    # 递归方法初始化流程
    def _init_context(self, file_path: str) -> NodeContext:
        vue_flow_json = self._read_json_file(file_path)
        if not vue_flow_json:
            return NodeContext()
        flow_context = FlowContext.model_validate(vue_flow_json)
        parent_context = NodeContext()
        parent_context.type = PROGRESS_NODE_TYPE
        parent_context.label = flow_context.label   # 若是子流程则使用流程名称作为节点名称
        # 当前节点只需要初始化输出参数定义即可
        for flow_output_param in flow_context.returns:
            output_param = Param()
            output_param.name = flow_output_param.name
            output_param.type = self._get_param_type(flow_output_param.type)
            output_param.path = flow_output_param.path
            output_param.value = flow_output_param.value
            output_param.desc = flow_output_param.desc
            output_param.type_def = flow_output_param.typeDef
            output_param.input_switch = flow_output_param.switch
            output_param.require = flow_output_param.require
            if output_param.name in parent_context.output_map:
                node_context = NodeContext()
                node_context.id = "progress"
                node_context.label = "流程"
                self._add_exception(parent_context, node_context, location="return",
                                    message=f"子节点返回值'{output_param.name}'重复定义")
            else:
                parent_context.output_map[output_param.name] = output_param
        current_context = FullContext()
        current_context.id = "start"
        edge_map: dict[str, list[Edge]] = defaultdict(list)
        #将Edge保存至hash表
        for flow_edge in flow_context.flow.edges:
            edge = Edge()
            edge.id = flow_edge.id
            edge.target = flow_edge.target
            edge_map[get_edge_key(flow_edge.source, flow_edge.sourceHandle)].append(edge)
        # 转换NodeContext对象
        has_start_node = False
        for node in flow_context.flow.nodes:
            if node.type != "pony":
                # 跳过非流程节点
                continue
            node_context = NodeContext()
            node_context.id = node.id
            node_context.label = node.data.label
            node_context.type = node.data.type
            if node.data.type == OFF_LINE_NODE_TYPE:
                # 跳过离线节点
                continue
            if node.id == START_NODE_ID and not has_start_node:
                if has_start_node:
                    self._add_exception(parent_context, node_context, location="content", message=f"流程中存在多个开始节点")
                else:
                    has_start_node = True
            if node.data.type == PROGRESS_NODE_TYPE:
                if not node.data.subPath:
                    self._add_exception(parent_context, node_context, location="content",message=f"未选择流程")
                    break
                else:
                    node_context = self._init_context(node.data.subPath[-1])
            else:
                if node.data.type not in self._node_dict:
                    self._add_exception(parent_context, node_context, location="content", message=f"缺失节点类型{node.data.type}")
                node_context.content, error_message_list = self._node_dict[node.data.type].convert_content(node.data.content, node.data.params, node.data.returns)
                if error_message_list:
                    self._add_exception(parent_context, node_context, location="content", message_list=error_message_list)
                for flow_output_param in node.data.returns:
                    output_param = Param()
                    output_param.name = flow_output_param.name
                    output_param.type = self._get_param_type(flow_output_param.type)
                    output_param.desc = flow_output_param.desc
                    output_param.type_def = flow_output_param.typeDef
                    if output_param.name in node_context.output_map:
                        self._add_exception(parent_context, node_context, location="return",message=f"返回值'{output_param.name}'重复定义")
                    else:
                        node_context.output_map[output_param.name] = output_param
                    node_context.label = node.data.label
            node_context.id = node.id
            current_context.node_context_map[node.id] = node_context
            # 节点作为子流程情况需要从新根据子节点定义更新入参的取值与出参的定义
            for flow_input_param in node.data.params:
                input_param = Param()
                input_param.name = flow_input_param.name
                input_param.type = self._get_param_type(flow_input_param.type)
                input_param.value = flow_input_param.value
                input_param.path = flow_input_param.path
                input_param.desc = flow_input_param.desc
                input_param.type_def = flow_input_param.typeDef
                input_param.input_switch = flow_input_param.switch
                input_param.require = flow_input_param.require
                if input_param.name in node_context.input_map:
                    self._add_exception(parent_context, node_context, location="param", message=f"入参'{input_param.name}'重复定义")
                else:
                    node_context.input_map[input_param.name] = input_param
            # 定义节点连接把手
            for flow_output_handler in node.data.handles:
                output_handler = OutputHandler()
                output_handler.name = flow_output_handler.name
                output_handler.edge_list = edge_map[get_edge_key(node.id, flow_output_handler.name)]
                node_context.handler_map[output_handler.name] = output_handler
            # 节点永远拥有默认的结束连接把手
            output_handler = OutputHandler()
            output_handler.name = END_HANDLE_NAME
            output_handler.edge_list = edge_map[get_edge_key(node.id, END_HANDLE_NAME)]
            node_context.handler_map[output_handler.name] = output_handler
        if not has_start_node:
            self._add_exception(parent_context, parent_context, location="content", message=f"流程中缺少开始节点")
        parent_context.sub_context = current_context
        self._close_json_file(file_path)
        return parent_context

    def init_context(self, parent_context: NodeContext):
        # 初始化全部子节点返回值
        for node_context in parent_context.sub_context.node_context_map.values():
            if node_context.type == PROGRESS_NODE_TYPE:
                for param_name, param in node_context.output_map.items():
                    path: list[str] = param.path
                    if  len(path) < 2:
                        self._add_exception(parent_context, node_context, location="param", message=f"子节点参数 '{param.name}' 未正确选择")
                        continue
                    node_id = path[0]
                    param_name = path[1]
                    if node_id not in node_context.sub_context.node_context_map:
                        self._add_exception(parent_context, node_context, location="param", message=f"子节点 '{param.name}' 选择的节点不存在")
                    elif param_name not in node_context.sub_context.node_context_map[node_id].output_map:
                        self._add_exception(parent_context, node_context, location="param", message=f"子节点 '{param.name}' 选择的参数不存在")
            for param_name, param in node_context.output_map.items():
                node_context.output_map[param_name] = ContextLoader._get_returns(param)
        # 初始化全部子节点入参
        for node_context in parent_context.sub_context.node_context_map.values():
            for param_name, param in node_context.input_map.items():
                node_context.input_map[param_name] = self._get_params(parent_context, node_context, param)
        # 递归初始化子流程
        for node_context in parent_context.sub_context.node_context_map.values():
            if node_context.type == PROGRESS_NODE_TYPE:
                self.init_context(node_context)

    @staticmethod
    def _get_returns(param: Param) -> Var:
        var: Var = Var()
        var.param_def = param
        if isinstance(param.type, ParamType):
            if param.type == ParamType.string or param.type == ParamType.json:
                # 字符串情况
                var.value = ""
                var.param_type = str
            elif param.type == ParamType.object:
                # 对象情况
                var.value = {}
                var.param_type = object
            elif param.type == ParamType.list:
                # 数组情况
                var.value = []
                var.param_type = list
            elif param.type == ParamType.dict:
                # 字典情况
                var.value = dict()
                var.param_type = dict
            elif param.type == ParamType.int:
                # 数字情况
                var.value = 0
                var.param_type = int
            elif param.type == ParamType.float:
                # 浮点情况
                var.value = 0.0
                var.param_type = float
            elif param.type == ParamType.bool:
                # 布尔情况
                var.value = True
                var.param_type = bool
            else:
                var.value = None
                var.param_type = object
        if isinstance(param.type, str):
            var.value = ''
            var.param_type = object
        var.param_def = param
        return var

    def _get_params(self, parent_context: NodeContext, node_context: NodeContext, param: Param) -> Var:
        if param.input_switch == InputSwitch.PATH or param.input_switch == InputSwitch.REPATH:
            if param.require is None:
                param.require = True
            if len(param.path) < 2 and param.require:
                self._add_exception(parent_context, node_context,location="param",message=f"必填入参 '{param.name}' 未选择值")
            elif len(param.path) == 2:
                # 获取路径参数
                path: list[str] = param.path
                node_id = path[0]
                param_name = path[1]
                if node_id == PARENT_NODE_ID:  # 从父级上下文中取到入参
                    if param_name not in parent_context.input_map:
                        self._add_exception(parent_context, node_context,location="param",message=f"不存在父级参数 '{param.name}'")
                    else:
                        return parent_context.input_map[param_name]
                else:  # 从节点中取到入参
                    if node_id not in parent_context.sub_context.node_context_map:
                        self._add_exception(parent_context, node_context,location="param",message=f"入参 '{param.name}' 选择的节点不存在")
                    elif param_name not in parent_context.sub_context.node_context_map[node_id].output_map:
                        self._add_exception(parent_context, node_context,location="param",message=f"入参 '{param.name}' 选择的参数不存在")
                    else:
                        return parent_context.sub_context.node_context_map[node_id].output_map[param_name]
            else:
                v = ContextLoader._get_returns(param)
                var = Var()
                var.value = v.value
                var.param_def = param
                var.param_type = v.param_type
                return var
        # param 不为选择参数 或 param不是必填参数的情况
        if param.require and param.input_switch != InputSwitch.PATH and param.input_switch != InputSwitch.REPATH and (param.value is None or param.value == '' or param.value == [] or param.value == {}):
            self._add_exception(parent_context, node_context,location="param",message=f"必填参数 '{param.name}' 未填写值")
        var = Var()
        var.value = param.value
        var.param_def = param
        var.param_type = ContextLoader._get_returns(param).param_type
        return var

    def _add_exception(self,parent_context: NodeContext, node_context: NodeContext, location:str, message:str = None, message_list: list[str] = None):
        if parent_context.label in self.error_messages:
            flow_error_dict = self.error_messages[parent_context.label]
        else:
            flow_error_dict = dict()
            self.error_messages[parent_context.label] = flow_error_dict

        if node_context.id in flow_error_dict:
            node_error_dict = flow_error_dict[node_context.id]
        else:
            node_error_dict = dict()
            flow_error_dict[node_context.id] = node_error_dict

        if "nodeLabel" not in node_error_dict:
            node_error_dict["nodeLabel"] = [node_context.label]

        if location in node_error_dict:
            messages = node_error_dict[location]
        else:
            messages = list()
            node_error_dict[location] = messages

        if message is not None:
            messages.append(message)
        if message_list is not None:
            messages += message_list
        self.is_success = False

    def _add_exception_static(self, location:str, message:str = None, message_list: list[str] = None):
        if "系统错误" in self.error_messages:
            flow_error_dict = self.error_messages["系统错误"]
        else:
            flow_error_dict = dict()
            self.error_messages["系统错误"] = flow_error_dict

        if location in flow_error_dict:
            node_error_dict = flow_error_dict[location]
        else:
            node_error_dict = dict()
            flow_error_dict[location] = node_error_dict

        if "nodeLabel" not in node_error_dict:
            node_error_dict["nodeLabel"] = [location]

        if location in node_error_dict:
            messages = node_error_dict["content"]
        else:
            messages = list()
            node_error_dict["content"] = messages

        if message is not None:
            messages.append(message)
        if message_list is not None:
            messages += message_list
        self.is_success = False