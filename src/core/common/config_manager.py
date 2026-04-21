import configparser
from pathlib import Path
import sys
import importlib

class ConfigManager:
    _instance = None
    _config_path: Path
    _base_path: Path
    _app_config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._base_path = Path(__file__).resolve().parent.parent.parent.parent
            # 配置文件路径（项目根目录下的config.ini）
            cls._instance._config_path = cls._instance._base_path / "config.ini"
            # 初始化配置
            cls._instance._initialize_config()
        return cls._instance

    def _initialize_config(self):
        """初始化配置，如果配置文件不存在则创建"""
        self._app_config = configparser.ConfigParser()

        if self._config_path.exists():
            self._app_config.read(self._config_path)
        else:
            # 创建默认配置（使用项目根目录下的相对路径）
            self._app_config['PATHS'] = {
                'project': str(self._base_path / "projects"),
                'gguf': str(self._base_path / "models/gguf"),
                'data': str(self._base_path / "data")
            }
            self.save_config()

    def save_config(self):
        """保存配置到INI文件"""
        with open(self._config_path, 'w') as configfile:
            self._app_config.write(configfile)

    def update_paths(self, project: str = None, gguf: str = None, data: str = None):
        """更新路径配置"""
        if project:
            self._app_config['PATHS']['project'] = self._resolve_path(project)
        if gguf:
            self._app_config['PATHS']['gguf'] = self._resolve_path(gguf)
        if data:
            self._app_config['PATHS']['data'] = self._resolve_path(data)

        self.save_config()
        self._reload_config_modules()

    def _resolve_path(self, path_str: str) -> str:
        """解析路径，处理_BASE_PATH占位符"""
        if path_str.startswith("_BASE_PATH/"):
            return str(self._base_path / path_str.split("/", 1)[1])
        return path_str

    def get_path(self, key: str) -> Path:
        """获取路径对象"""
        return Path(self._app_config['PATHS'].get(key, ''))

    def get_config(self) -> dict:
        """获取当前配置字典"""
        return {
            'project': self._app_config['PATHS']['project'],
            'gguf': self._app_config['PATHS']['gguf'],
            'data': self._app_config['PATHS']['data']
        }

    def _reload_config_modules(self):
        """重新加载所有导入配置的模块"""
        # 更新当前模块的配置
        if 'src.core.common.config_manager' in sys.modules:
            importlib.reload(sys.modules['src.core.common.config_manager'])
        elif 'config_manager' in sys.modules:
            importlib.reload(sys.modules['config_manager'])

        # 更新其他模块的配置引用
        for module_name, module in list(sys.modules.items()):
            if hasattr(module, 'PROJECT_PATH'):
                module.PROJECT_PATH = self.get_path('project')
            if hasattr(module, 'GGUF_PATH'):
                module.GGUF_PATH = self.get_path('gguf')
            if hasattr(module, 'DATA_PATH'):
                module.DATA_PATH = self.get_path('data')

# 单例实例
config_manager = ConfigManager()

# 导出路径变量
PROJECT_PATH = config_manager.get_path('project')
GGUF_PATH = config_manager.get_path('gguf')
DATA_PATH = config_manager.get_path('data')