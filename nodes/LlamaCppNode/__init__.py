from .node_def.llama_cpp_loader import LlamaCppLoader
from .node_def.llama_cpp_generate import LlamaGenerate


NODE_CLASSES = {
    "LLAMA_CPP_LOADER": LlamaCppLoader,
    "LLAMA_GENERATE": LlamaGenerate,
}