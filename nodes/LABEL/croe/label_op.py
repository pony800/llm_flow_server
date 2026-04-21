import re
from enum import Enum
from typing import Dict, List, Union, Optional, Tuple

class LabelType(Enum):
    LABEL = 'label'  # 普通标签
    STR = 'str'  # 字符串标签
    NUM = 'num'  # 数字标签


class Label:
    __slots__ = ('id', 'value', 'type')

    def __init__(self, id: int, value: Union[str, int, float, None], type: LabelType):
        self.id = id
        self.value = value
        self.type = type

    def __repr__(self):
        return f"Label(id={self.id}, value={self.value}, type={self.type.value})"


class ConditionNode:
    """条件表达式节点基类"""

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        raise NotImplementedError()


class NotCondition(ConditionNode):
    """取反条件节点"""
    __slots__ = ('child',)

    def __init__(self, child: ConditionNode):
        self.child = child

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        return not self.child.evaluate(labels)

    def __repr__(self):
        return f"!({self.child})"


class LiteralCondition(ConditionNode):
    """字面值条件节点"""
    __slots__ = ('value')

    def __init__(self, value: bool):
        self.value = value

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        return self.value


class AtomicCondition(ConditionNode):
    """原子条件节点"""
    __slots__ = ('label_name', 'op', 'expected_value', 'expected_type')

    def __init__(self, label_name: str, op: str = None, expected_value: Union[str, int, float] = None):
        self.label_name = label_name
        self.op = op  # 如: None, '=', '>', '<', '>=', '<='
        self.expected_value = expected_value

        # 根据预期值推断类型
        if expected_value is None:
            self.expected_type = LabelType.LABEL
        elif isinstance(expected_value, (int, float)):
            self.expected_type = LabelType.NUM
        else:
            self.expected_type = LabelType.STR

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        # 标签不存在
        if self.label_name not in labels:
            return False

        label = labels[self.label_name]

        # 普通标签存在即满足
        if self.expected_type == LabelType.LABEL:
            return True

        # 类型不匹配
        if label.type != self.expected_type:
            return False

        # 等值判断
        if self.op in (None, '='):
            return label.value == self.expected_value

        # 数值比较
        if self.expected_type == LabelType.NUM and isinstance(label.value, (int, float)):
            actual_val = label.value
            expected_val = self.expected_value

            # 转换类型确保兼容
            if isinstance(actual_val, int) and isinstance(expected_val, float):
                actual_val = float(actual_val)
            elif isinstance(actual_val, float) and isinstance(expected_val, int):
                expected_val = float(expected_val)

            # 执行比较
            if self.op == '>':
                return actual_val > expected_val
            if self.op == '<':
                return actual_val < expected_val
            if self.op == '>=':
                return actual_val >= expected_val
            if self.op == '<=':
                return actual_val <= expected_val

        return False


class CompoundCondition(ConditionNode):
    """复合条件节点"""
    __slots__ = ('operator', 'children')

    def __init__(self, operator: str, children: List[ConditionNode]):
        self.operator = operator  # 'AND', 'OR'
        self.children = children

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        if self.operator == 'AND':
            return all(child.evaluate(labels) for child in self.children)
        if self.operator == 'OR':
            return any(child.evaluate(labels) for child in self.children)
        return False

    def __repr__(self):
        return f"({f' {self.operator} '.join(map(str, self.children))})"


class CountCondition(ConditionNode):
    """数量条件节点"""
    __slots__ = ('min_count', 'conditions')

    def __init__(self, min_count: int, conditions: List[ConditionNode]):
        self.min_count = min_count
        self.conditions = conditions

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        true_count = sum(1 for cond in self.conditions if cond.evaluate(labels))
        return true_count >= self.min_count

    def __repr__(self):
        return f"#{self.min_count}{{{', '.join(map(str, self.conditions))}}}"


class ExpressionNode:
    """表达式节点基类"""

    def evaluate(self, labels: Dict[str, Label]) -> Union[int, float, str, None]:
        raise NotImplementedError()


class ConstantExpression(ExpressionNode):
    """常量值表达式节点"""
    __slots__ = ('value',)

    def __init__(self, value: Union[int, float, str]):
        self.value = value

    def evaluate(self, labels: Dict[str, Label]) -> Union[int, float, str, None]:
        return self.value


class LabelExpression(ExpressionNode):
    """标签表达式节点"""
    __slots__ = ('label_name',)

    def __init__(self, label_name: str):
        self.label_name = label_name

    def evaluate(self, labels: Dict[str, Label]) -> Union[int, float, str, None]:
        if self.label_name in labels:
            return labels[self.label_name].value
        return None


class BinaryExpression(ExpressionNode):
    """二元运算表达式节点"""
    __slots__ = ('left', 'operator', 'right')

    def __init__(self, left: ExpressionNode, operator: str, right: ExpressionNode):
        self.left = left
        self.operator = operator  # '+', '-', '*', '/'
        self.right = right

    def evaluate(self, labels: Dict[str, Label]) -> Union[int, float, str, None]:
        # print(f"[二元运算] 开始计算: {self.left} {self.operator} {self.right}")

        # 计算左操作数
        left_val = self.left.evaluate(labels)
        # print(f"[左操作数] 结果: {left_val} (类型: {type(left_val)})")

        # 计算右操作数
        right_val = self.right.evaluate(labels)
        # print(f"[右操作数] 结果: {right_val} (类型: {type(right_val)})")

        # 如果任意一个操作数不存在，返回None
        if left_val is None or right_val is None:
            # print(f"[二元运算] 错误: 操作数缺失 (左: {left_val}, 右: {right_val})")
            return None

        # 数值运算
        if self.operator in ('+', '-', '*', '/'):
            # 尝试转换为数值
            try:
                left_num = float(left_val) if isinstance(left_val, str) and left_val.replace('.', '',
                                                                                             1).isdigit() else left_val
                right_num = float(right_val) if isinstance(right_val, str) and right_val.replace('.', '',
                                                                                                 1).isdigit() else right_val

                # print(f"[数值转换] 左: {left_num} (类型: {type(left_num)}), 右: {right_num} (类型: {type(right_num)})")

                if not isinstance(left_num, (int, float)) or not isinstance(right_num, (int, float)):
                    # 转换为字符串进行拼接
                    if self.operator == '+':
                        result = str(left_val) + str(right_val)
                        # print(f"[字符串拼接] 结果: {result}")
                        return result
                    raise ValueError(f"非数值类型不支持 {self.operator} 运算")

                if self.operator == '+':
                    result = left_num + right_num
                elif self.operator == '-':
                    result = left_num - right_num
                elif self.operator == '*':
                    result = left_num * right_num
                elif self.operator == '/':
                    if right_num == 0:
                        # print(f"[除法错误] 除零错误")
                        return None
                    result = left_num / right_num

                # print(f"[数值计算] 结果: {result}")
                return result
            except ValueError as e:
                # print(f"[数值转换错误] {e}")
                # 数值转换失败，如果是加法则进行字符串拼接
                if self.operator == '+':
                    result = str(left_val) + str(right_val)
                    # print(f"[字符串拼接] 结果: {result}")
                    return result
                # print(f"[运算错误] 非数值类型不支持 {self.operator} 运算")
                return None

        # print(f"[二元运算] 未知运算符: {self.operator}")
        return None


class ComparisonCondition(ConditionNode):
    """比较条件节点"""
    __slots__ = ('left', 'operator', 'right')

    def __init__(self, left: ExpressionNode, operator: str, right: ExpressionNode):
        self.left = left
        self.operator = operator  # '>', '<', '>=', '<=', '==', '!='
        self.right = right

    def evaluate(self, labels: Dict[str, Label]) -> bool:
        left_val = self.left.evaluate(labels)
        right_val = self.right.evaluate(labels)

        # 如果任意一个操作数不存在，返回False
        if left_val is None or right_val is None:
            return False

        # 尝试数值比较
        try:
            left_num = float(left_val) if isinstance(left_val, str) and left_val.replace('.', '',
                                                                                         1).isdigit() else left_val
            right_num = float(right_val) if isinstance(right_val, str) and right_val.replace('.', '',
                                                                                             1).isdigit() else right_val

            if isinstance(left_num, (int, float)) and isinstance(right_num, (int, float)):
                if self.operator == '>':
                    return left_num > right_num
                if self.operator == '<':
                    return left_num < right_num
                if self.operator == '>=':
                    return left_num >= right_num
                if self.operator == '<=':
                    return left_num <= right_num
                if self.operator == '==':
                    return left_num == right_num
                if self.operator == '!=':
                    return left_num != right_num
        except (ValueError, TypeError):
            pass

        # 字符串比较
        if self.operator == '==':
            return str(left_val) == str(right_val)
        if self.operator == '!=':
            return str(left_val) != str(right_val)

        return False


class Operation:
    """操作基类"""

    def execute(self, manager: 'LabelManager'):
        raise NotImplementedError()


class LabelOperation(Operation):
    """标签操作"""
    __slots__ = ('label_name', 'action', 'value', 'expression')

    def __init__(self, label_name: str, action: str, value: Union[str, int, float, None] = None,
                 expression: ExpressionNode = None):
        self.label_name = label_name
        self.action = action  # 'ADD', 'SET', 'REMOVE', 'INCREMENT'
        self.value = value
        self.expression = expression  # 表达式赋值

    def execute(self, manager: 'LabelManager'):
        labels = manager.label_map
        # print(f"[标签操作] 执行: {self.label_name}, 动作: {self.action}")
        # 表达式赋值
        if self.expression is not None:
            # print(f"[表达式赋值] 开始计算表达式: {self.expression}")
            result = self.expression.evaluate(labels)
            # print(f"[表达式赋值] 计算结果: {result}")

            if result is not None:
                # 确定标签类型
                if isinstance(result, (int, float)):
                    label_type = LabelType.NUM
                elif isinstance(result, str):
                    label_type = LabelType.STR
                else:
                    label_type = LabelType.LABEL

                # print(f"[表达式赋值] 标签类型: {label_type.value}")

                # 设置标签值
                if self.label_name in labels:
                    label = labels[self.label_name]
                    # print(f"[更新标签] {self.label_name}: 旧值={label.value} (类型={label.type.value}), 新值={result} (类型={label_type.value})")
                    label.type = label_type
                    label.value = result
                else:
                    manager.last_id += 1
                    # print(f"[添加标签] {self.label_name}: 值={result} (类型={label_type.value}), ID={manager.last_id}")
                    labels[self.label_name] = Label(manager.last_id, result, label_type)
            else:
                # print(f"[表达式赋值] 错误: 表达式计算结果为None")
                raise ValueError("表达式计算结果为None")
            return

        # 移除标签
        if self.action == 'REMOVE':
            if self.label_name in labels:
                del labels[self.label_name]
            return

        # 添加标签
        if self.action == 'ADD':
            # 确定标签类型
            if self.value is None:
                label_type = LabelType.LABEL
            elif isinstance(self.value, (int, float)):
                label_type = LabelType.NUM
            else:
                label_type = LabelType.STR

            # 添加新标签或覆盖现有标签
            if self.label_name in labels:
                existing = labels[self.label_name]
                existing.type = label_type
                existing.value = self.value
            else:
                manager.last_id += 1
                labels[self.label_name] = Label(manager.last_id, self.value, label_type)
            return

        # 设置标签值
        if self.action == 'SET':
            if self.label_name not in labels:
                return

            label = labels[self.label_name]

            # 根据值类型确定新类型
            if self.value is None:
                new_type = LabelType.LABEL
            elif isinstance(self.value, (int, float)):
                new_type = LabelType.NUM
            else:
                new_type = LabelType.STR

            label.type = new_type
            label.value = self.value
            return

        # 数值增减操作
        if self.action == 'INCREMENT':
            if self.label_name not in labels:
                return

            label = labels[self.label_name]

            # 确保是数字标签
            if label.type != LabelType.NUM or not isinstance(label.value, (int, float)):
                label.type = LabelType.NUM
                label.value = 0

            # 执行数值操作
            if isinstance(self.value, (int, float)):
                label.value += self.value
            return


class SetOperation(Operation):
    """集合约束操作"""
    __slots__ = ('max_count', 'conditions')

    def __init__(self, max_count: int, conditions: List[ConditionNode]):
        self.max_count = max_count
        self.conditions = conditions

    def execute(self, manager: 'LabelManager'):
        labels = manager.label_map

        # 找出当前满足的条件
        satisfied_conditions = [cond for cond in self.conditions if cond.evaluate(labels)]

        # 如果满足的条件数量超过限制
        if len(satisfied_conditions) > self.max_count:
            # 收集所有关联的标签及其添加时间
            related_labels = {}
            for cond in satisfied_conditions:
                self._collect_labels(cond, related_labels, manager)

            # 如果没有收集到标签，直接返回
            if not related_labels:
                return

            # 按照添加时间排序（从小到大）
            sorted_labels = sorted(related_labels.items(), key=lambda x: x[1].id)

            # 需要移除的标签数量
            remove_count = len(satisfied_conditions) - self.max_count

            # 移除最旧的标签
            for label_name, label_obj in sorted_labels[:remove_count]:
                if label_name in labels:
                    del labels[label_name]

    def _collect_labels(self, cond: ConditionNode, labels: Dict[str, Label], manager: 'LabelManager'):
        """递归收集条件中的所有标签名"""
        if isinstance(cond, AtomicCondition):
            label = manager.get_label(cond.label_name)
            if label:
                # 记录标签对象而不仅仅是名称
                labels[cond.label_name] = label
        elif isinstance(cond, (CompoundCondition, CountCondition, ComparisonCondition)):
            if hasattr(cond, 'children'):
                for child in cond.children:
                    self._collect_labels(child, labels, manager)
            elif hasattr(cond, 'left') and hasattr(cond, 'right'):
                # 处理比较条件
                if hasattr(cond.left, 'label_name'):
                    label = manager.get_label(cond.left.label_name)
                    if label:
                        labels[cond.left.label_name] = label
                if hasattr(cond.right, 'label_name'):
                    label = manager.get_label(cond.right.label_name)
                    if label:
                        labels[cond.right.label_name] = label


class RuleModel:
    """规则模型"""
    __slots__ = ('condition', 'operations', 'set_operations')

    def __init__(self,
                 condition: ConditionNode,
                 operations: List[Operation],
                 set_operations: List[SetOperation]):
        self.condition = condition
        self.operations = operations
        self.set_operations = set_operations

    def execute(self, manager: 'LabelManager'):
        """执行规则"""
        # print(f"[规则执行] 检查条件: {self.condition}")
        condition_result = self.condition.evaluate(manager.label_map)
        # print(f"[规则执行] 条件结果: {condition_result}")

        # 检查条件是否满足
        if condition_result:
            # print(f"[规则执行] 条件满足，执行 {len(self.operations)} 个操作")

            # 执行所有基础操作
            for i, op in enumerate(self.operations, 1):
                # print(f"[操作 {i}/{len(self.operations)}] 开始执行")
                op.execute(manager)
                # print(f"[操作 {i}/{len(self.operations)}] 执行完成")

            # print(f"[规则执行] 执行 {len(self.set_operations)} 个集合操作")
            # 执行所有集合操作
            for i, set_op in enumerate(self.set_operations, 1):
                # print(f"[集合操作 {i}/{len(self.set_operations)}] 开始执行")
                set_op.execute(manager)
                # print(f"[集合操作 {i}/{len(self.set_operations)}] 执行完成")
        else:
            pass
            # print(f"[规则执行] 条件不满足，跳过操作")


class RuleParser:
    """规则解析器"""

    @staticmethod
    def parse_condition(expr: str) -> ConditionNode:
        """解析条件表达式"""
        expr = RuleParser._preprocess(expr)
        return RuleParser._parse_logical_expr(expr)

    @staticmethod
    def parse_operations(ops_str: str) -> Tuple[List[Operation], List[SetOperation]]:
        """解析操作语句"""
        operations = []
        set_operations = []

        # 分割操作语句
        ops = RuleParser._split_operations(ops_str)

        for op_str in ops:
            # 集合约束操作
            if op_str.startswith('^'):
                max_count, conditions = RuleParser._parse_set_operation(op_str)
                set_operations.append(SetOperation(max_count, conditions))
            # 标签操作
            else:
                operations.extend(RuleParser._parse_label_operation(op_str))

        return operations, set_operations

    @staticmethod
    def _preprocess(expr: str) -> str:
        """预处理表达式：移除多余空格，保留引号内内容"""
        # 使用正则表达式匹配引号内容并临时替换
        parts = []
        last_end = 0
        for match in re.finditer(r"'(.*?)'", expr):
            # 添加引号前的内容
            parts.append(expr[last_end:match.start()].replace(' ', ''))
            # 添加引号内容（保留内部空格）
            parts.append(f"'{match.group(1)}'")
            last_end = match.end()
        # 添加剩余内容
        parts.append(expr[last_end:].replace(' ', ''))
        return ''.join(parts)

    @staticmethod
    def _parse_expression(expr: str) -> ExpressionNode:
        """解析表达式（算术表达式）"""
        expr = expr.strip()
        # print(f"[解析表达式] 开始解析表达式: '{expr}'")

        # 尝试解析为数值常量
        if expr.replace('.', '', 1).replace('-', '', 1).isdigit():
            # print(f"[数值常量] 解析为数值常量: {expr}")
            try:
                if '.' in expr:
                    return ConstantExpression(float(expr))
                else:
                    return ConstantExpression(int(expr))
            except ValueError:
                pass

        # 尝试解析为字符串常量
        if expr.startswith("'") and expr.endswith("'"):
            # print(f"[字符串常量] 解析为字符串常量: {expr}")
            return ConstantExpression(expr[1:-1])

        # 尝试解析为标签名
        if re.match(r'^[\w\u4e00-\u9fff_]+$', expr):
            # print(f"[标签表达式] 解析为标签名: {expr}")
            return LabelExpression(expr)

        # 处理括号表达式
        if expr.startswith('(') and expr.endswith(')'):
            # print(f"[括号表达式] 发现括号: {expr}")
            inner_expr = expr[1:-1].strip()
            # print(f"[括号表达式] 递归解析内部表达式: '{inner_expr}'")
            return RuleParser._parse_expression(inner_expr)

        # 处理二元运算
        operators = [
            ('+', '-'),  # 优先级较低
            ('*', '/')  # 优先级较高
        ]

        # 按优先级处理运算符（从低优先级开始）
        for ops in operators:
            depth = 0  # 括号深度
            # 从右向左扫描运算符
            for i in range(len(expr) - 1, -1, -1):
                char = expr[i]
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1

                # 当不在括号内且找到运算符时
                if depth == 0 and char in ops:
                    # print(f"[二元运算] 在位置 {i} 找到运算符 '{char}'")
                    left_part = expr[:i].strip()
                    right_part = expr[i + 1:].strip()

                    # print(f"[二元运算] 左操作数: '{left_part}'")
                    # print(f"[二元运算] 右操作数: '{right_part}'")

                    if left_part and right_part:
                        left = RuleParser._parse_expression(left_part)
                        right = RuleParser._parse_expression(right_part)
                        return BinaryExpression(left, char, right)
                    else:
                        # print(f"[二元运算] 错误: 操作数不完整")
                        raise ValueError("二元运算错误: 操作数不完整")

        # 默认作为标签处理
        # print(f"[默认处理] 作为标签处理: {expr}")
        return LabelExpression(expr)

    @staticmethod
    def _parse_atomic_condition(expr: str) -> ConditionNode:
        """解析原子条件"""
        expr = expr.strip()

        # 处理取反操作符
        if expr.startswith('!'):
            inner_cond = RuleParser._parse_atomic_condition(expr[1:].strip())
            return NotCondition(inner_cond)

        # 处理括号表达式（递归解析）
        if expr.startswith('(') and expr.endswith(')'):
            return RuleParser._parse_logical_expr(expr[1:-1].strip())

        # 处理#k{}条件
        if expr.startswith('#'):
            match = re.match(r'^#(\d+)\{(.+)}$', expr)
            if match:
                min_count = int(match.group(1))
                conditions_str = match.group(2).strip()
                conditions = []
                current = []
                depth = 0

                # 解析逗号分隔的条件
                for char in conditions_str:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1
                    elif char == ',' and depth == 0:
                        part = ''.join(current).strip()
                        if part:
                            conditions.append(RuleParser._parse_atomic_condition(part))
                        current = []
                        continue
                    current.append(char)

                # 添加最后一个条件
                last_part = ''.join(current).strip()
                if last_part:
                    conditions.append(RuleParser._parse_atomic_condition(last_part))

                return CountCondition(min_count, conditions)

        # 处理布尔字面量
        if expr == 'True':
            return LiteralCondition(True)
        if expr == 'False':
            return LiteralCondition(False)

        # 处理标签间比较
        for op in ['>=', '<=', '==', '!=', '>', '<']:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left_expr = RuleParser._parse_expression(parts[0].strip())
                    right_expr = RuleParser._parse_expression(parts[1].strip())
                    return ComparisonCondition(left_expr, op, right_expr)

        # 存在判断: 标签名 - 修改这里支持带下划线的标签格式
        if re.match(r'^[\w\u4e00-\u9fff_]+$', expr):
            return AtomicCondition(expr)

        # 优先匹配比较操作符: 标签名:>值, 标签名:>=值, 标签名:<值, 标签名:<=值
        # 修改正则以支持带下划线的标签格式
        match = re.match(r'^([\w\u4e00-\u9fff_]+):([><]=?)(-?\d+\.?\d*)$', expr)
        if match:
            label_name, op, value_str = match.groups()
            try:
                value = float(value_str) if '.' in value_str else int(value_str)
                return AtomicCondition(label_name, op, value)
            except ValueError:
                # 数值转换失败，保留原始字符串
                return AtomicCondition(label_name, op, value_str)

        # 匹配等值判断: 标签名:值 或 标签名:'值'
        # 修改正则以支持带下划线的标签格式
        match = re.match(r'^([\w\u4e00-\u9fff_]+):(=?)(\'?)([^:]+)\3$', expr)
        if match:
            label_name, op, quote, value_str = match.groups()
            # 字符串值
            if quote == "'":
                return AtomicCondition(label_name, '=', value_str)
            # 数值
            if value_str.replace('.', '', 1).replace('-', '', 1).isdigit():
                try:
                    value = float(value_str) if '.' in value_str else int(value_str)
                    return AtomicCondition(label_name, '=', value)
                except ValueError:
                    pass
            # 普通标签
            return AtomicCondition(label_name, '=', value_str)

        # 尝试匹配带括号的表达式（如 "标签e:>0"）
        # 修改正则以支持带下划线的标签格式
        match = re.match(r'^([\w\u4e00-\u9fff_]+):([><]=?)(-?\d+\.?\d*)$', expr)
        if match:
            label_name, op, value_str = match.groups()
            try:
                value = float(value_str) if '.' in value_str else int(value_str)
                return AtomicCondition(label_name, op, value)
            except ValueError:
                pass

        raise ValueError(f"无效的条件表达式: {expr}")

    @staticmethod
    def _parse_logical_expr(expr: str) -> ConditionNode:
        """解析逻辑表达式（AND/OR）"""
        expr = expr.strip()

        # 检查整个表达式是否被括号包围
        if expr.startswith('(') and expr.endswith(')'):
            # 检查括号是否平衡
            depth = 0
            valid = True
            for i, char in enumerate(expr):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0 and i < len(expr) - 1:
                        # 在结束前深度为0，说明不是整个表达式被括号包围
                        valid = False
                        break

            if valid and depth == 0:
                # 去掉最外层括号
                return RuleParser._parse_logical_expr(expr[1:-1].strip())

        # 尝试按 OR 拆分（优先级最低）
        or_parts = []
        start = 0
        depth = 0  # 括号嵌套深度
        for i, char in enumerate(expr):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif depth == 0 and i > 0 and expr.startswith('||', i - 1):
                # 找到 OR 运算符（且不在括号内）
                part = expr[start:i - 1].strip()
                if part:
                    or_parts.append(part)
                start = i + 1

        # 添加最后一部分
        last_part = expr[start:].strip()
        if last_part:
            or_parts.append(last_part)

        if len(or_parts) > 1:
            return CompoundCondition('OR', [
                RuleParser._parse_logical_expr(part)
                for part in or_parts
            ])

        # 尝试按 AND 拆分
        and_parts = []
        start = 0
        depth = 0  # 括号嵌套深度
        for i, char in enumerate(expr):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif depth == 0 and i > 0 and expr.startswith('&&', i - 1):
                # 找到 AND 运算符（且不在括号内）
                part = expr[start:i - 1].strip()
                if part:
                    and_parts.append(part)
                start = i + 1

        # 添加最后一部分
        last_part = expr[start:].strip()
        if last_part:
            and_parts.append(last_part)

        if len(and_parts) > 1:
            return CompoundCondition('AND', [
                RuleParser._parse_logical_expr(part)
                for part in and_parts
            ])

        # 否则当作原子条件处理
        return RuleParser._parse_atomic_condition(expr)

    @staticmethod
    def _split_operations(ops_str: str) -> List[str]:
        """分割操作语句"""
        operations = []
        current = []
        depth = 0  # 括号深度
        in_quote = False  # 是否在引号内

        for char in ops_str:
            if char == "'":
                in_quote = not in_quote
            elif char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
            elif char == ';' and depth == 0 and not in_quote:
                operations.append(''.join(current))
                current = []
                continue
            current.append(char)

        if current:
            operations.append(''.join(current))

        return operations

    @staticmethod
    def _parse_label_operation(op_str: str) -> List[Operation]:
        """解析标签操作"""
        # 移除操作: -标签
        if op_str.startswith('-'):
            label_name = op_str[1:]
            return [LabelOperation(label_name, 'REMOVE')]

        # 添加操作: +标签 / +标签:值
        action = 'ADD' if op_str.startswith('+') else 'SET'
        if op_str.startswith('+'):
            op_str = op_str[1:]

        # 不带值的操作: 标签
        if ':' not in op_str:
            return [LabelOperation(op_str, action)]

        # 带值的操作: 标签:值
        label_name, value_str = op_str.split(':', 1)
        label_name = label_name.strip()
        value_str = value_str.strip()

        # 表达式赋值：严格检查括号包裹
        if value_str.startswith('(') and value_str.endswith(')'):
            try:
                expression = RuleParser._parse_expression(value_str)
                return [LabelOperation(label_name, action, expression=expression)]
            except Exception:
                # 解析失败，继续尝试其他类型
                pass

        # 数值增减操作
        if value_str.startswith(('+', '-')) and value_str[1:].replace('.', '', 1).isdigit():
            try:
                value = float(value_str)
                return [LabelOperation(label_name, 'INCREMENT', value)]
            except ValueError:
                pass

        # 字符串值 - 修复这里：严格匹配单引号包裹的字符串
        if value_str.startswith("'") and value_str.endswith("'"):
            # 确保整个字符串被单引号包裹并且中间没有未闭合的引号
            if len(value_str) >= 2 and value_str.count("'") % 2 == 0:
                # 只取第一个引号和最后一个引号之间的内容
                value = value_str[1:-1]
                return [LabelOperation(label_name, action, value)]

        # 数值 - 修复这里：确保整个字符串是数字
        if value_str.replace('.', '', 1).replace('-', '', 1).isdigit():
            try:
                value = float(value_str) if '.' in value_str else int(value_str)
                return [LabelOperation(label_name, action, value)]
            except ValueError:
                pass

        # 普通标签更新
        return [LabelOperation(label_name, action, value_str)]
    @staticmethod
    def _parse_set_operation(op_str: str) -> Tuple[int, List[ConditionNode]]:
        """解析集合约束操作"""
        match = re.match(r'^\^(\d+)\{(.+)}$', op_str)
        if not match:
            raise ValueError(f"无效的集合操作: {op_str}")

        max_count = int(match.group(1))
        conditions_str = match.group(2)
        conditions = []
        pos = 0
        depth = 0  # 括号深度
        current = []

        # 解析逗号分隔的条件
        for char in conditions_str:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                part = ''.join(current).strip()
                if part:
                    conditions.append(RuleParser.parse_condition(part))
                current = []
                continue
            current.append(char)

        # 添加最后一个条件
        last_part = ''.join(current).strip()
        if last_part:
            conditions.append(RuleParser.parse_condition(last_part))

        return max_count, conditions


class LabelManager:
    def __init__(self):
        self.last_id = 0
        self.label_map: Dict[str, Label] = {}
        self.rule_list: List[RuleModel] = []

    @staticmethod
    def prefix_labels(expr: str, group: str) -> str:
        """
        为表达式中的所有标签添加分组前缀
        格式：分组名_标签名
        注意：
          1. 如果标签已经有分组前缀（包含下划线），则不再添加
          2. 不处理关键字（True/False）和数字
          3. 保留字符串常量（引号内内容）不变
          4. 跳过表达式部分（括号内的内容）
        """
        # 如果group为空，直接返回原表达式
        if not group:
            return expr

        # 定义关键字列表
        keywords = {'True', 'False'}

        # 定义替换函数
        def replace(match: re.Match) -> str:
            label_name = match.group(0)
            # 跳过关键字
            if label_name in keywords:
                return label_name
            # 跳过数字开头的标识符
            if label_name[0].isdigit():
                return label_name
            # 如果标签已有下划线（有分组前缀），则不做处理
            if '_' in label_name:
                return label_name
            # 否则添加分组前缀
            return f"{group}_{label_name}"

        # 标签名正则：匹配中文、英文、数字和下划线
        pattern = re.compile(r'[a-zA-Z_\u4e00-\u9fff][a-zA-Z0-9_\u4e00-\u9fff]*')

        # 分割字符串，保留引号内的内容和表达式部分
        parts = []
        last_index = 0
        depth = 0  # 括号深度
        in_quote = False  # 是否在引号内

        # 手动控制索引遍历
        i = 0
        while i < len(expr):
            char = expr[i]

            # 处理括号深度
            if char == '(' and not in_quote:
                depth += 1
            elif char == ')' and not in_quote:
                depth -= 1

            # 处理引号内容
            if char == "'":
                if not in_quote:
                    # 开始引号
                    in_quote = True
                    # 处理引号前的内容
                    non_expr_part = expr[last_index:i]
                    non_expr_part_replaced = pattern.sub(replace, non_expr_part)
                    parts.append(non_expr_part_replaced)
                    last_index = i
                else:
                    # 结束引号
                    in_quote = False
                    # 添加引号内容（原样）
                    quoted_content = expr[last_index:i + 1]
                    parts.append(quoted_content)
                    last_index = i + 1
            i += 1

        # 添加剩余部分
        remaining = expr[last_index:]
        if remaining:
            # 只在不在引号内且括号平衡时处理替换
            if not in_quote and depth == 0:
                remaining_replaced = pattern.sub(replace, remaining)
                parts.append(remaining_replaced)
            else:
                parts.append(remaining)

        return ''.join(parts)

    def add_rule(self, rule: str, group: str = 'default'):
        """添加永久规则"""
        rule = "".join(rule.split())
        rule_model = self._compile_rule(rule, group)
        self.rule_list.append(rule_model)

    def exec_rule(self, rule: str, group: str = 'default'):
        """
        执行临时规则语句
        只执行传入的规则，不执行永久规则
        """
        rule = "".join(rule.split())
        rule_model = self._compile_rule(rule, group)
        self._exec(rule_model)

    def exec_permanent_rules(self):
        """
        执行永久更新规则
        遍历执行所有已添加的永久规则
        """
        for rule in self.rule_list:
            self._exec(rule)

    def _compile_rule(self, rule: str, group: str = 'default') -> RuleModel:
        """编译规则"""
        rule = rule.strip()
        # 更宽松的规则格式检查
        if not rule.startswith('[') or ']:[' not in rule or not rule.endswith(']'):
            raise ValueError("规则格式错误，必须是[条件]:[操作]格式")

        # 找到条件部分和操作部分分界点
        condition_end = rule.find(']:[')
        if condition_end == -1:
            raise ValueError("规则格式错误，必须包含']:['分隔符")

        # 提取条件部分 (移除开头的'[')
        condition_str = rule[1:condition_end]
        # 提取操作部分 (移除结尾的']')
        operation_str = rule[condition_end + 3:-1]

        # 为标签添加分组前缀
        condition_str = self.prefix_labels(condition_str, group)
        operation_str = self.prefix_labels(operation_str, group)

        # 解析条件
        condition = RuleParser.parse_condition(condition_str)

        # 解析操作
        operations, set_operations = RuleParser.parse_operations(operation_str)

        return RuleModel(condition, operations, set_operations)

    def _exec(self, rule: RuleModel):
        """执行规则模型"""
        rule.execute(self)

    def label_dict(self) -> Dict[str, Dict[str, Label]]:
        """
        返回分组字典
        格式：dict[分组名称, dict[标签名称, 标签对象]]
        注意：标签名称是去掉分组前缀后的名称
        """
        result = {}
        for full_name, label in self.label_map.items():
            # 如果没有下划线，则整个作为标签名，分组为'default'
            if '_' in full_name:
                # 只分割一次（第一个下划线）
                parts = full_name.split('_', 1)
                group_name = parts[0]
                tag_name = parts[1]
            else:
                group_name = 'default'
                tag_name = full_name

            # 确保分组存在
            if group_name not in result:
                result[group_name] = {}
            # 添加标签
            result[group_name][tag_name] = label

        return result

    # 辅助方法
    def get_label(self, name: str) -> Optional[Label]:
        return self.label_map.get(name)

    def add_label(self, name: str, value: Union[str, int, float, None] = None):
        """直接添加标签（测试用）"""
        self.last_id += 1
        if value is None:
            label_type = LabelType.LABEL
        elif isinstance(value, str):
            label_type = LabelType.STR
        else:
            label_type = LabelType.NUM

        self.label_map[name] = Label(self.last_id, value, label_type)

    def __repr__(self):
        labels = ', '.join(f"{k}:{v}" for k, v in self.label_map.items())
        return f"LabelManager(labels=[{labels}], rules={len(self.rule_list)})"

    def print_labels(self):
        """打印所有标签"""
        print("当前标签:")
        for name, label in self.label_map.items():
            print(f"  {label.id} {name}: {label.value} ({label.type.value})")

# 测试标签管理器
if __name__ == "__main__":
    # 创建标签管理器
    manager = LabelManager()

    # 添加标签 aaa, bbb:3.14, ccc:'我的世界'
    manager.exec_rule("[True]:[+aaa;+bbb:3.14;+ccc:'我的世界']")
    manager.print_labels()

    # 移除标签 aaa
    manager.exec_rule("[True]:[-aaa]")
    manager.print_labels()

    # 条件判断执行
    manager.exec_rule("[bbb > 0]:[bbb:1]")
    manager.print_labels()

    # 同时只保留k个标签,删除最开始添加的那个
    manager.exec_rule("[True]:[+ddd:13;^2{aaa,bbb,ccc,ddd==13}]")
    manager.print_labels()

    # 将语句添加为永久规则
    manager.add_rule("[aaa || ddd:13]:[+eee:14]")
    # 按添加顺序执行永久规则
    manager.exec_permanent_rules()
    manager.print_labels()

    # 使用其他分组空间, 在其他分组空间内可以通过 group_label 来使用其他分组的标签数据
    manager.exec_rule("[default_ccc=='我的世界']:[+aaa:1;+bbb:2; +default_fff:'跨分组添加标签']", group="test")
    manager.print_labels()

    # 满足n个条件时执行
    manager.exec_rule("[#2{aaa,bbb,ccc,ddd} && default_ddd>12]:[+eee;default_ddd:-10]", group="test")
    manager.print_labels()

    manager.exec_rule("[default_ccc!='粉色羊']:[+fff]", group="test")
    manager.print_labels()

    manager.exec_rule("[!ggg && eee]:[+ggg]", group="test")
    manager.print_labels()