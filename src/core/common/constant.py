PARENT_NODE_ID = "#parent" # 下拉选择数据路径时, nodeId = parent代表父级资源
PROGRESS_NODE_TYPE = "PROGRESS" # node的type类型为progress时节点为子流程类型
OFF_LINE_NODE_TYPE = "OFF_LINE" # 被屏蔽流程的节点
START_NODE_ID = "#start"  # 每个流程中有且只有一个节点id为#start
END_HANDLE_NAME = "end" # 每个流程中有且只有一个handler为end
STOP_HANDLE_NAME = "stop" # 当流程返回handler为stop时停止执行后续流程
