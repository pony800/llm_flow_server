from .node_def.stdio import Stdio
from nodes.Operation.node_def.script import Script
from nodes.Operation.node_def.jinja_two import Jinja2
from nodes.Operation.node_def.get_params_xml import GetParamsXml
from nodes.Operation.node_def.unbox import UnBox
from nodes.Operation.node_def.dialogue_manage import DialogueManage

NODE_CLASSES = {
    "STDIO": Stdio,
    "DIALOGUE_MANAGE": DialogueManage,
    "SCRIPT": Script,
    "JINJA2": Jinja2,
    "UNBOX": UnBox,
    "GET_PARAMS_XML": GetParamsXml,
}