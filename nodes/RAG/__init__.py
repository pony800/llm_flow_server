from .node_def.rag_loader import RagLoader
from .node_def.rag_add import RagAdd
from .node_def.rag_search import RagSearch
from .node_def.rag_add_batch import RagAddBatch
from .node_def.rag_delete import RagDelete
from .node_def.rag_delete_batch import RagDeleteBatch

NODE_CLASSES = {
    "RAG_LOADER": RagLoader,
    "RAG_ADD": RagAdd,
    # "RAG_ADD_BATCH": RagAddBatch,
    "RAG_DELETE": RagDelete,
    "RAG_DELETE_BATCH": RagDeleteBatch,
    "RAG_SEARCH": RagSearch,
}