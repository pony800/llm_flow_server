from typing import TypeVar

from src.api.schemas.response.base_vo import ResultVO

T = TypeVar('T')

def success(data: T) -> ResultVO[T]:  # 直接使用类型变量T
    re = ResultVO[T]()  # 明确指定泛型类型
    re.code = 200
    re.message = "请求成功"
    re.data = data
    return re

def fail(message: str, code:int = 500) -> ResultVO:  # 直接使用类型变量T
    re = ResultVO()  # 明确指定泛型类型
    re.code = code
    re.message = message
    return re