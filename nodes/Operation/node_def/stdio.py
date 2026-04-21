from typing import List, Literal, Tuple

from pydantic import BaseModel, ConfigDict

from src.core.abstractions.node_interface import NodeInterface
from src.models.computation.context import NodeContext, ReturnParam
from src.models.computation.vue_flow import NodeData, FlowInputParam, FlowOutputParam

from src.core.websocket.websocket_agent import WebSocketAgent
from src.tools.ws_message_tools import WsMessageTool
#stdio对象
class ControlModel(BaseModel):
  id: str = ""
  type: str = ""
  name: str = ""
  icon: str = ""
  value: object = ""
  width: int = 1
  height: int = 1
  paramsType: Literal['input', 'output', 'change']|None = None
  paramsName: str = ""
  model_config = ConfigDict(
      extra="allow",  # 允许未在模型中定义的字段
      arbitrary_types_allowed=True
  )

class Content(BaseModel):
    controlModelList:List[ControlModel] = []
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Stdio(NodeInterface):
    """
    """
    @staticmethod
    async def run(context:NodeContext,  ws: WebSocketAgent) -> ReturnParam:
        if not isinstance(context.content, Content):
            await ws.send_json(WsMessageTool.error(context, "context.content is not of type Content"))
            raise TypeError(f"context.content is not of type Content {context.label}")
        content: Content = context.content
        await ws.send_json(WsMessageTool.position(context))

        returnParam = ReturnParam()

        try:
            controlList:List[ControlModel] = context.content.controlModelList
            inputValueMap:dict[str, object] = {}
            outputValueList: List[str] = []
            print (context.input_map)

            for controller in controlList:
                if 'change' == controller.paramsType and controller.paramsName in context.input_map:
                    # 输入输出参数(展示值并允许修改)
                    inputValueMap[controller.id] = context.input_map[controller.paramsName].value
                    outputValueList.append(controller.id)
                elif 'input' == controller.paramsType and controller.paramsName in context.input_map:
                    # 输入参数(仅展示值)
                    inputValueMap[controller.id] = context.input_map[controller.paramsName].value
                elif 'output' == controller.paramsType and controller.paramsName in context.output_map:
                    # 输出参数(输出为新变量) 输出参数带出默认值
                    inputValueMap[controller.id] = controller.value
                    outputValueList.append(controller.id)

            await ws.send_json(WsMessageTool.set_content(context, "STDIO", context.content))
            await ws.send_json(WsMessageTool.put_values(context, inputValueMap))
            await ws.send_json(WsMessageTool.get_values(context, outputValueList))
            json: dict[str, object] = await ws.receive_json()
            for var in context.output_map.values():
                var.value = None
            for controller in controlList:
                if 'change' == controller.paramsType and controller.paramsName in context.input_map and controller.id in json:
                    # 修改输入变量的值
                    context.input_map[controller.paramsName].value = json[controller.id]
                elif 'output' == controller.paramsType and controller.paramsName in context.output_map and controller.id in json:
                    # 输出为新变量
                    context.output_map[controller.paramsName].value = json[controller.id]
        except Exception as e:
            await ws.send_json(WsMessageTool.error(context, str(e)))

        return returnParam

    @staticmethod
    def convert_content(obj: dict, params: list[FlowInputParam], returns: list[FlowOutputParam]) -> Tuple[Content, List[str]]:
        if obj is None:
            content = Content()
        else:
            content = Content.model_validate(obj)

        error_list = []
        param_set : set[str] = set()
        return_set : set[str] = set()
        for param in params:
            param_set.add(param.name)
        for return_param in returns:
            return_set.add(return_param.name)

        for item in content.controlModelList:
            if item.paramsName == "":
                error_list.append(f"控件 {item.name}({item.id}) 未绑定参数")
            elif item.paramsType == 'change' or item.paramsType == 'input':
                if item.paramsName not in param_set:
                    error_list.append(f"绑定入参 {item.paramsName} 不存在")
            elif item.paramsType == 'output':
                if item.paramsName not in return_set:
                    error_list.append(f"绑定返回值 {item.paramsName} 不存在")

        return content, error_list

    @staticmethod
    def get_init_node_data() -> NodeData:
        #基本信息
        node_data = NodeData()
        node_data.type = "STDIO"
        node_data.label = "标准输入输出"
        node_data.desc = "流程运行时的主要界面,功能如下\n1.当流程运行到此处时弹出标准输入输出界面\n2.可以在一定程度上自定义界面布局\n3.可以 展示/修改 流程中的参数,也可将用户输入定义为新的参数\n注:该节点将长期维护,添加更多实用功能(如表格,图表等)"
        node_data.content = Content()
        node_data.canAddParams = True
        node_data.canAddReturns = True
        #输入参数
        #输出参数
        #连接器
        return node_data
