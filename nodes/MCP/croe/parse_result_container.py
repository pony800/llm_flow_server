from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from collections import OrderedDict
import json
import ast
import re
from typing import Dict, Any

# ======================
# 枚举定义
# ======================
class OperationType(Enum):
    TOOL = "tool"
    QUERY = "query"
    OPERATE = "operate"

# ======================
# 统一操作对象
# ======================
@dataclass
class Operation:
    step_id: str
    type: OperationType
    operation: str  # 原tool_name/question/operation的合并字段
    params: Dict[str, Any]
    exec_str: str  # 原始标签内容

# ======================
# 解析结果容器
# ======================
class ParseResultContainer:
    def __init__(self):
        self.operations: OrderedDict[str, Operation] = OrderedDict()
        self.is_success: Optional[bool] = None
        self.message: str = ""

    def _add_operation(self, step_id: str, operation: Operation):
        self.operations[step_id] = operation

    def pop_operation(self) -> Optional[Tuple[str, Operation]]:
        if not self.operations:
            return None
        step_id = next(iter(self.operations))  # 获取第一个key
        return step_id, self.operations.pop(step_id)

    def check_out(self) -> bool:
        if len(self.operations) == 0 and self.is_success is None:
            return True #未通过检查
        else:
            return False #通过检查

    def parse_mcp_output(self, output: str):
        self.operations = OrderedDict()
        self.is_success = None
        self.message = ""

        """解析MCP协议输出"""
        tag_pattern = re.compile(
            r'(<tool\s+id="(.*?)"\s+call="(.*?)">(.*?)</tool>)|'
            r'(<query\s+id="(.*?)">(.*?)</query>)|'
            r'(<operate\s+id="(.*?)">(.*?)</operate>)|'
            r'(<end\s+state="(success|fail)"\s+message="(.*?)"\s*/>)',
            re.DOTALL
        )

        for match in tag_pattern.finditer(output):
            groups = match.groups()

            # 处理工具调用
            if groups[0] is not None:
                operate = Operation(
                    step_id=groups[1],
                    type=OperationType.TOOL,
                    operation=groups[2],  # tool_name
                    params=self._parse_params(groups[3]),
                    exec_str=groups[0].strip()
                )
                self._add_operation(groups[1], operate)  # step_id作为key

            # 处理用户询问
            elif groups[4] is not None:
                operate = Operation(
                    step_id=groups[5],
                    type=OperationType.QUERY,
                    operation=groups[6].strip(),  # question
                    params={},
                    exec_str=groups[4].strip()
                )
                self._add_operation(groups[5], operate)

            # 处理用户操作
            elif groups[7] is not None:
                operate = Operation(
                    step_id=groups[8],
                    type=OperationType.OPERATE,
                    operation=groups[9].strip(),  # operation desc
                    params={},
                    exec_str=groups[7].strip()
                )
                self._add_operation(groups[8], operate)


            elif groups[10]:  # 新版结束标签
                self.is_success = (groups[11] == "success")
                self.message = groups[12].strip('"')

    @staticmethod
    def _parse_params(param_str: str) -> Dict[str, Any]:
        """增强版参数解析器，支持复杂场景：
        1. 无引号的JSON对象（{name:value}）
        2. 带转义字符的路径（C:\\Users\\）
        3. 多层嵌套数据结构
        4. 被额外引号包裹的JSON（"[]"）
        """
        params = {}
        # 改进后的正则，支持含逗号的复杂值
        pattern = re.compile(r'(\w+)=("[^"]*"|\S+?)(?=\s*,\s*\w+=|$)')

        for key, value in re.findall(pattern, param_str):
            raw_value = value.strip()

            # 处理被多余引号包裹的情况（如query_list="[]"）
            if (raw_value.startswith('"') and raw_value.endswith('"')) or \
                    (raw_value.startswith("'") and raw_value.endswith("'")):
                inner_value = raw_value[1:-1]
                if inner_value:
                    raw_value = inner_value

            # 尝试解析JSON（兼容无引号key）
            try:
                # 修复无引号key的JSON（如{name:value} -> {"name":"value"}）
                json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)',
                                  lambda m: f"{m.group(1)}\"{m.group(2)}\"{m.group(3)}",
                                  raw_value)
                params[key] = json.loads(json_str)
                continue
            except json.JSONDecodeError:
                pass

            # 处理基本类型
            try:
                # 布尔值处理（兼容True/False）
                if raw_value.lower() in ('true', 'false'):
                    params[key] = raw_value.lower() == 'true'
                    continue

                # 数字类型（包括科学计数法）
                parsed = ast.literal_eval(raw_value)
                if isinstance(parsed, (int, float)):
                    params[key] = parsed
                    continue
            except (ValueError, SyntaxError):
                pass

            # 处理Windows路径（保留原始反斜杠）
            if '\\' in raw_value and not raw_value.startswith(('{', '[')):
                params[key] = raw_value.replace('\\\\', '\\')
                continue

            # 最终回退：保留原始值
            params[key] = raw_value

        return params


# ======================
# 使用示例
# ======================
if __name__ == "__main__":
    sample_output = """
    为了完成这个任务，我们需要先确定操作系统的类型，因为不同的操作系统桌面路径可能不同。然后我们将在该路径下创建一个Java项目的目录结构，通常包含src、lib等子目录以及一些基础的Java源代码文件。

首先，让我们查看系统类型以决定下一步如何进行。
<tool id="step-1" call="show_os"></tool>
    现在我们知道操作系统是Windows。在Windows上，桌面的默认路径通常是C:\\Users\<用户名>\Desktop。为了创建一个Java项目，我们需要在这个路径下创建一个新的文件夹，并且包含一些基础结构如src目录和可能的一个简单的Java源代码文件。

由于我们不知道具体的用户名，我需要询问您当前使用的用户名是什么。
<query id="step-2">请告诉我您的Windows用户名。</query>
    知道了用户名后，我们可以开始在桌面上创建Java项目。首先，在C:\\Users\\admin\Desktop路径下创建一个名为MyJavaProject的文件夹，并在其内部创建必要的目录结构和文件。

接下来，我将执行以下步骤：

创建主项目文件夹。
在该文件夹内创建src子文件夹。
在src中创建一个简单的Java源代码文件作为示例。
<tool id="step-3" call="create_file">file_path={"aaa":"bbb","ccc":12}</tool>
<tool id="step-4" call="get_phone_list">query_list=[{name:"bbb"},{"name":"aaa"}],age=18</tool>

接下来，我将在src目录下创建一个简单的Java源代码文件作为示例。
<tool id="step-5" call="create_file">file_path="C:\\Users\\admin\Desktop\MyJavaProject\src\Main.java",name="asd"</tool>
<end state="success" message="找到3个日志文件"/>
    """


    result = ParseResultContainer()
    result.parse_mcp_output(sample_output)

    while result.operations:
        step_id, op = result.pop_operation()
        print(op.exec_str)
        print(f"{op.step_id}: {op.type.name} - {op.operation}")
        if op.params:
            print(f"   参数: {op.params}")

    print(f"最终状态: {result.is_success}, 消息: {result.message}")