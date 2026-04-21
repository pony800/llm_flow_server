from pydantic import BaseModel, ConfigDict
from src.models.enums.vue_flow_enum import InputSwitch, ParamType

class Position(BaseModel):
    x: float | None = 0
    y: float | None = 0
    zoom: float | None = 0.5
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

class FlowEdge(BaseModel):
    id: str|None = None
    source: str|None = None  # sourceNodeId
    target: str|None = None  # targetNodeId
    sourceHandle: str|None = None  # sourceHandleId
    targetHandle: str|None = None  # targetHandleId 暂时不用
    type: str = "pony"
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

class FlowInputParam(BaseModel):
    name: str = "var"
    type: ParamType | str = ParamType.string
    desc: str = ""
    typeDef: str = "string"
    value: object|None = None
    path: list[str] = []
    switch: InputSwitch = InputSwitch.PATH
    selectList: list[str] = []
    editable: bool = False
    require: bool = True
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

class FlowOutputParam(BaseModel):
    name: str = "return"
    type: ParamType | str = ParamType.string
    desc: str = ""
    typeDef: str = "string"
    editable: bool = False
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

class FlowOutputHandle(BaseModel):
    name: str = "handle"
    label: str = "条件判断"
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

class NodeData(BaseModel):
    label: str = "Node"
    group: str = ""
    hasNext: bool = True    # 是否展示next_handler
    hasStart: bool = True   # 是否展示start_handler
    desc: str = ""  # 节点简介
    type: str = "START"   # 如果该节点不是子流程则这里的 type 生效
    subPath: list[str] | None = [] # 子流程地址
    params: list[FlowInputParam] = []
    returns: list[FlowOutputParam] = []
    content: object|None = None
    handles: list[FlowOutputHandle] = []
    canAddParams: bool = False
    canAddReturns: bool = False
    locked: bool = False
    switch: InputSwitch|None = None # 规定添加入参的选择方式
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

class FlowNode(BaseModel):
    id: str = ""
    type: str = ""   # 子流程时 type = "PROGRESS"
    data: NodeData|None = None
    initialized: bool|None = None
    position: Position|None = None
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

#工作流对象
class Flow(BaseModel):
    edges: list[FlowEdge] = []
    nodes: list[FlowNode] = []
    viewport: Position = Position()
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

#当前流程上下文对象
class FlowContext(BaseModel):
    filePath: str | None = None
    label: str | None = None
    flow: Flow = Flow()
    params: list[FlowOutputParam] = []
    returns: list[FlowInputParam] = []
    model_config = ConfigDict(
        extra = "ignore",  # 允许未在模型中定义的字段
    )

