from dataclasses import dataclass, field
from typing import List
from enum import Enum

# 外部函数定义
@dataclass
class FunParam:
    name: str   #参数名称
    type: str  #参数类型
    desc: str  #参数描述

@dataclass
class Function:
    handle_name: str = ""   #连接名称
    name: str = ""   #函数名称
    desc: str = ""   #函数功能描述
    params: List[FunParam] = field(default_factory = list)      #参数列表
    returns: List[FunParam] = field(default_factory = list)   #返回值列表

#执行计划历史
@dataclass
class Plan:
    exec_str: str       #模型调用字符串
    is_success: bool    #是否执行成功
    returns: str | None
    response: str | None

#对话历史
@dataclass
class Dialogue:
    role: str       #对话角色
    content: str    #对话内容

@dataclass
class DialogueExec:
    step_id: str
    status: str
    returns: str | None
    response: str | None

class AgentType(str, Enum):
    QUERY = "query"     #查询函数定义
    FUN_DEF = "fun"     #返回函数定义
    EXEC = "exec"       #执行函数
    RETURN = "return"   #返回执行结果

@dataclass
class AgentData:
    operation_type: AgentType   #操作类型
    call_name: str = "" #调用函数名称
    function: Function = ""  #返回函数定义
    params: dict[str, any] = ""  #调用工具时的入参和返回参数
    status: bool = ""     #工具调用是否成功
    message: str = ""    #工具返回错误信息或成功信息
