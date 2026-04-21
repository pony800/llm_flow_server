from enum import Enum
class ContextState(Enum):
    INIT = 1
    READY = 2
    START = 3
    COMPLETE = 4
    CANCELLED = 5