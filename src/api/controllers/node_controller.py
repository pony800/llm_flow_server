from src.api.schemas.response.base_vo import ResultVO
from src.tools import result_tools
from src.core.nodes.node_loader import node_loader

async def get_nodes_data() -> ResultVO:
    re_list = []
    for dir_name, dir_content in node_loader.modules.items():
        node_list = []
        re_list.append({
            'type': dir_name,
            'nodeList': node_list,
        })
        for node_name, node in dir_content.items():
            node_list.append({
                'nodeName': node_name,
                'nodeData': node.get_init_node_data(),
            })
    return result_tools.success(re_list)