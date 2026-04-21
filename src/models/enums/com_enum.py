from enum import Enum

class WsExecType(str, Enum):
    GET = 'get',    #获取参数
    PUT = 'put',    #放置参数
    ADD = 'add',    #追加参数
    PUT_ALL = 'put_all' #设置全部参数
    CONTENT = 'content',    #直接设置内容
    RUN_TIME_ERROR = 'run_time_error',#报告错误
    EXCEPTION = 'exception', #编译错误
    POSITION = 'position',#报告位置

class FileType(str, Enum):
    FLOW = 'FLOW',
    GGUF = 'GGUF',
    DATA = 'DATA',
