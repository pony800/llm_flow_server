from __future__ import annotations
from typing import Generic, TypeVar, List
from pydantic import BaseModel
from src.models.enums.com_enum import WsExecType

T = TypeVar('T')

class WsExecVO(BaseModel):
    nodeId: str = ""
    nodeType: str = ""
    nodeName: str = ""
    operateType: WsExecType = WsExecType.POSITION
    message: str = ""
    keys: List[str] = []
    data: dict[str, object] = {}
    content: object = {}
    errorMessages: dict[str, dict[str, List[str]]] = {}

class ResultVO(BaseModel, Generic[T]):
    code: int = 200
    message: str = "请求成功"
    data: T|None = None