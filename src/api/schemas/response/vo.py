from __future__ import annotations
from pydantic import BaseModel

class PathVO(BaseModel):
    path: str|None = None
    name: str | None = None
    isDir: bool = False

class PathTreeVO(BaseModel):
    path: str = ""
    name: str = ""
    isDir: bool = False
    disabled: bool = False
    children: list[PathTreeVO] = []