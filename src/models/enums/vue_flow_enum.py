from enum import Enum

class InputSwitch(Enum):
    PATH = "path"
    REPATH = "reverse"
    VALUE = "value"
    SELECT = 'select'
    INT = "number"
    FLOAT = "float"
    BOOL = "bool"
    FILE = "file"

class ParamType(Enum):
    object= "Object"
    string= "String"
    json= "Json"
    int= "Int"
    bool= "Bool"
    float= "Float"
    enum= "Enum"
    dict= "Dict"
    list= "List"
    gguf= "GGUF"

