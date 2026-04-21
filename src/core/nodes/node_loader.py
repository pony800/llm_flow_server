import importlib.util
import sys
from pathlib import Path

from src.core.abstractions.node_interface import NodeInterface
# 节点加载器

class NodeLoader:

    def __init__(self):
        self.nodes: dict[str, NodeInterface] = {}  # 存储加载的节点 {node_name: node_class}
        self.modules: dict[str, dict[str, NodeInterface]] = {}

    def load_nodes(self, models_dir="nodes"):
        """动态加载指定目录下的所有节点工程"""
        models_path = Path(models_dir)
        print(f"正在加载节点目录: {models_path.absolute()}")

        # 遍历models目录下的所有子目录
        for node_dir in models_path.iterdir():
            if node_dir.name.startswith("_"):
                # 跳过非公开文件
                continue
            if node_dir.is_dir():
                # 检查是否存在必要的初始化文件
                init_file = node_dir / "__init__.py"
                if not init_file.exists():
                    print(f"跳过无效节点目录: {node_dir.name} (缺少__init__.py)")
                    continue
                # 动态加载模块
                module_name = f"{models_dir}.{node_dir.name}"  # 构建模块路径
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    str(init_file)  # 将Path对象转换为字符串路径
                )

                if spec is None:
                    print(f"无法加载模块: {module_name}")
                    continue

                try:
                    # 创建并执行模块
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module  # 注册到全局模块系统
                    spec.loader.exec_module(module)
                except Exception as e:
                    print(f"加载节点 {node_dir.name} 失败: {str(e)}")
                    continue

                # 验证模块的有效性
                if not hasattr(module, "NODE_CLASSES"):
                    print(f"节点 {node_dir.name} 缺少NODE_CLASSES声明")
                    continue

                current_node_map:dict[str, NodeInterface] = {}
                self.modules[node_dir.name] = current_node_map
                # 注册节点类
                for node_name, node_cls in module.NODE_CLASSES.items():
                    if node_name in self.nodes:
                        print(f"节点名称冲突: {node_name} 已存在")
                        continue
                    current_node_map[node_name] = node_cls
                    self.nodes[node_name] = node_cls

node_loader = NodeLoader()
node_loader.load_nodes()