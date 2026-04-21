import os
from pathlib import Path
from typing import List
from src.api.schemas.response.vo import PathTreeVO


def build_directory_tree(path: Path, suffix: List[str], base_path: Path) -> PathTreeVO:
    """重构后的目录树构建方法，同一层级中目录在前，文件在后"""
    tree = PathTreeVO(
        name=path.name,
        path=str(Path(path).relative_to(base_path)).replace(os.sep, '/'),
        isDir=True,
        children=[]
    )

    try:
        # 先收集所有条目
        entries = list(os.scandir(path))

        # 分离目录和文件
        dirs = []
        files = []

        for item in entries:
            if item.is_dir():
                dirs.append(item)
            else:
                if len(suffix) == 0 or item.name.split('.')[-1].lower() in suffix:
                    files.append(item)

        # 先处理目录
        for dir_item in dirs:
            tree.children.append(build_directory_tree(Path(dir_item.path), suffix, base_path))

        # 再处理文件
        for file_item in files:
            tree.children.append(PathTreeVO(
                path=str(Path(file_item.path).relative_to(base_path)).replace(os.sep, '/'),
                name=file_item.name,
                isDir=False,
                children=[]
            ))

        if not tree.children:
            tree.disabled = True
    except (PermissionError, FileNotFoundError):
        pass
    return tree