from typing import List

from src.models.enums.com_enum import WsExecType
from src.models.computation.context import NodeContext
from src.api.schemas.response.base_vo import WsExecVO


class WsMessageTool:
    @staticmethod
    def exception(error_data: dict[str, dict[str, dict[str, List[str]]]]) -> dict:
        wsExecVO = WsExecVO()
        wsExecVO.operateType = WsExecType.EXCEPTION
        wsExecVO.errorMessages = error_data
        return wsExecVO.model_dump()

    @staticmethod
    def error(node:NodeContext, message:str) -> dict:
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.RUN_TIME_ERROR
        wsExecVO.message = message
        return wsExecVO.model_dump()

    @staticmethod
    def position(node:NodeContext) -> dict:
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.POSITION
        return wsExecVO.model_dump()

    @staticmethod
    def put(node: NodeContext, key: str, value: object):
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.PUT
        wsExecVO.data = {key: value}
        return wsExecVO.model_dump()

    @staticmethod
    def put_values(node: NodeContext, data: dict[str, object]):
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.PUT_ALL
        wsExecVO.data = data
        return wsExecVO.model_dump()

    @staticmethod
    def add(node: NodeContext, key: str, value: object):
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.ADD
        wsExecVO.data = {key: value}
        return wsExecVO.model_dump()

    @staticmethod
    def get(node: NodeContext, key: str):
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.GET
        wsExecVO.keys = [key]
        return wsExecVO.model_dump()

    @staticmethod
    def set_content(node: NodeContext, node_type: str, content: any):
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node_type
        wsExecVO.nodeName = node.label
        wsExecVO.content = content
        wsExecVO.operateType = WsExecType.CONTENT
        return wsExecVO.model_dump()

    @staticmethod
    def get_values(node: NodeContext, keys: List[str]):
        wsExecVO = WsExecVO()
        wsExecVO.nodeId = node.id
        wsExecVO.nodeType = node.type
        wsExecVO.nodeName = node.label
        wsExecVO.operateType = WsExecType.GET
        wsExecVO.keys = keys
        return wsExecVO.model_dump()