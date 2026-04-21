from __future__ import annotations
from typing import Generic, TypeVar
from pydantic import BaseModel
T = TypeVar('T')

class WsExecQO(BaseModel):
    nodeId: str = ""
    name: str|None = None
    value: object|None = None
    data: object = {}

class PathUpdateRequest(BaseModel):
    project: str = None
    gguf: str = None
    data: str = None