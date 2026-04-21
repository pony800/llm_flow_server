from dataclasses import dataclass, field
from enum import Enum
from llama_cpp import Llama
from nodes.RAG.croe.rag import RAGService


# 外部函数定义
class RagState(str, Enum):
    QUERY = "query"     #查询函数定义
    FUN_DEF = "fun"     #返回函数定义
    EXEC = "exec"       #执行函数
    RETURN = "return"   #返回执行结果

@dataclass
class RagData:
    rag_service: RAGService | None = None   #操作类型
    embedding_model: Llama | None = None
    emb_str: str | None = None
    emb_vec: list[float] | None = field(default_factory=list)
    state: RagState = RagState.QUERY
