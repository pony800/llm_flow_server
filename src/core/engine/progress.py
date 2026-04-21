from src.core.engine.context_loader import ContextLoader
from src.core.common.constant import PROGRESS_NODE_TYPE, START_NODE_ID, END_HANDLE_NAME, STOP_HANDLE_NAME
from src.core.nodes.node_loader import NodeLoader
from src.models.enums.context_enum import ContextState
from src.models.computation.context import NodeContext, ReturnParam
from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool


class Progress:
    # 初始化进程
    def __init__(self, node_loader: NodeLoader, ws: WebSocketAgent):
        self._context_loader = ContextLoader(node_dict=node_loader.nodes)
        self._ws = ws
        self._node_loader = node_loader
        self._parent_context:NodeContext = NodeContext()
        # 流程引擎初始化为初始状态
        self._state = ContextState.INIT

    async def open_flow(self, file_path:str) -> bool:
        # 从json文件加载流程
        self._parent_context = self._context_loader.loader_new_context(file_path=file_path)
        # 对流程全局初始化
        self._context_loader.init_context(parent_context=self._parent_context)
        self._state = ContextState.READY
        if not self._context_loader.is_success:
            print(self._context_loader.error_messages)
            await self._ws.send_json(WsMessageTool.exception(self._context_loader.error_messages))
            return False
        return True

    async def exec(self, start_node_id: str):
        """执行主逻辑"""
        if self._state != ContextState.READY:
            await self._ws.send_json("无法重复执行")
            return
        # print(self._parent_context.model_dump_json(indent=4))
        self._state = ContextState.START
        # 运行当前节点
        await self._run(self._parent_context, start_node_id)


    #流程递归执行器
    async def _run(self, current_context: NodeContext, start_node_id: str) -> ReturnParam:
        current_context.sub_context.start_list.append(current_context.sub_context.node_context_map[start_node_id])
        while current_context.sub_context.start_list:
            # 从待执行列表中获取下一个需要执行的节点
            current_node_context = current_context.sub_context.start_list.pop()
            if current_node_context is None:
                continue
            # 根据节点类型不同调用节点组件进行处理
            if current_node_context.type == PROGRESS_NODE_TYPE:
                # 子流程直接递归调用自己进行处理
                await self._ws.send_json(WsMessageTool.position(current_node_context))
                return_param = await self._run(current_node_context, START_NODE_ID)
            else:
                return_param = await self._node_loader.nodes[current_node_context.type].run(current_node_context, self._ws)
            # 根据返回值来决定下一个节点的位置并将其加入 start_list
            if not return_param.is_finish:
                #如果为未结束立即将自己放入待执行列表
                current_context.sub_context.start_list.append(current_node_context)
            if return_param.handler_name == STOP_HANDLE_NAME:
                # 如果节点返回stop则无需继续向后执行
                continue
            handler_name = END_HANDLE_NAME if return_param.is_finish else return_param.handler_name
            for next_edge in current_node_context.handler_map[handler_name].edge_list:
                current_context.sub_context.start_list.append(current_context.sub_context.node_context_map[next_edge.target])
        #节点执行完毕, 返回结果
        for name, output_param in current_context.output_map.items():
            if output_param.param_def is None:
                continue
            path: list[str] = output_param.param_def.path
            if path:
                output_param.value = current_context.sub_context.node_context_map[path[0]].output_map[path[1]].value
        return_param = ReturnParam()
        return_param.is_finish = True
        return return_param