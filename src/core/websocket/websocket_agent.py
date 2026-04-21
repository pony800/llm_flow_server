import asyncio
from typing import Any
from fastapi import WebSocket

class WebSocketAgent:
    def __init__(self, websocket: WebSocket):
        """
        代理 FastAPI WebSocket 对象
        :param websocket: 被代理的原始 WebSocket 对象
        """
        self._websocket = websocket

    async def send_json(self, data: Any) -> None:
        """
        发送 JSON 数据（完全代理原始方法）
        发送后主动让出事件循环控制权
        """
        await self._websocket.send_json(data)
        await asyncio.sleep(0)

    async def receive_json(self) -> Any:
        """
        接收 JSON 数据（完全代理原始方法）
        同步等待直到收到消息
        """
        return await self._websocket.receive_json()

    async def receive_text(self) -> Any:
        """
        接收 JSON 数据（完全代理原始方法）
        同步等待直到收到消息
        """
        return await self._websocket.receive_text()

    async def close(self) -> None:
        """关闭连接（代理原始方法）"""
        await self._websocket.close()

    @property
    def client(self) -> Any:
        """访问原始客户端信息（代理原始属性）"""
        return self._websocket.client

    async def __aenter__(self):
        """支持异步上下文管理"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时自动关闭"""
        await self.close()