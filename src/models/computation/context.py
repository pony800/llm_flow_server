from __future__ import annotations 
from pydantic import BaseModel, ConfigDict, field_serializer
from src.core.common.constant import END_HANDLE_NAME
from src.models.enums.vue_flow_enum import ParamType, InputSwitch


class Edge(BaseModel):
    id: str = ""
    target: str = ""  # NodeContext.id
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Param(BaseModel):
    name: str = ""
    type: ParamType | str = ParamType.string
    path: list[str] = [] #如果path中有值则调用取值函数将值放入value中
    desc: str = ""
    type_def: str|None = None
    value: object|None = None
    is_path: bool = True #值是否来自path
    input_switch: InputSwitch = InputSwitch.PATH
    require: bool = True
    model_config = ConfigDict(arbitrary_types_allowed=True)

class Var(BaseModel):
    value: object = 0
    param_type: type = str
    param_def: Param = {}
    @field_serializer("param_type")
    def serialize_type(self, value: type, _info) -> str:
        return f"{value.__module__}.{value.__name__}"

class OutputHandler(BaseModel):
    name: str = ""
    edge_list: list[Edge] = []
    model_config = ConfigDict(arbitrary_types_allowed=True)

class NodeContext(BaseModel):
    id: str = ""
    label: str = ""
    type: str = ""
    content: object = {}
    input_map: dict[str, Param|Var] = {}   #key:参数名
    output_map: dict[str, Param|Var] = {}   #key:参数名
    handler_map: dict[str, OutputHandler] = {}  #key:把手名
    sub_context: FullContext|None = None #子流程上下文
    model_config = ConfigDict(arbitrary_types_allowed=True)

class FullContext(BaseModel):
    id: str = ""
    node_context_map: dict[str, NodeContext] = {}  # map<id, nodeContext>
    start_list: list[NodeContext] = []  # 待执行节点id列表
    model_config = ConfigDict(arbitrary_types_allowed=True)

class ReturnParam(BaseModel):
    is_finish: bool = True #当该节点结束运行时请将此值设置为 True, 否则该节点会立马加入待执行列表
    handler_name: str = END_HANDLE_NAME #当 is_finish = False 时, handler参数必传
    model_config = ConfigDict(arbitrary_types_allowed=True)

#声明引用的类
NodeContext.model_rebuild()
FullContext.model_rebuild()