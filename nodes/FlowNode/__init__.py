from .node_def.start import Start
from .node_def.if_else import IfElse
from .node_def.for_i import ForI
from .node_def.for_list import ForList
from .node_def.for_dict import ForDict
from .node_def.for_while import ForWhile
from .node_def.params import Params
from .node_def.for_text import ForTxt

NODE_CLASSES = {
    "START": Start,
    "IF_ELSE": IfElse,
    "FOR_I": ForI,
    "FOR_LIST": ForList,
    "FOR_DICT": ForDict,
    "FOR_WHILE": ForWhile,
    "FOR_TXT": ForTxt,
    "PARAMS": Params,
}