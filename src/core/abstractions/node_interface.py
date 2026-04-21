from abc import ABC, abstractmethod
from typing import Tuple, List

from src.models.computation.context import NodeContext, ReturnParam
from src.core.websocket.websocket_agent import WebSocketAgent
from src.models.computation.vue_flow import FlowInputParam, FlowOutputParam


class NodeInterface(ABC):
    @staticmethod
    @abstractmethod
    async def run(context:NodeContext, ws: WebSocketAgent) -> ReturnParam:
        pass

    @staticmethod
    @abstractmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[object, List[str]]:
        pass

    @staticmethod
    @abstractmethod
    def get_init_node_data() -> object:
        pass