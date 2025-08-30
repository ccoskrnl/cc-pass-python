from enum import Enum, auto


class OperandType(Enum):
    VOID = auto()

    VAR = auto()
    SSA_VAR = auto()

    BOOL = auto()
    FLOAT = auto()
    INT = auto()
    STR = auto()

    PTR = auto()

    ARGS = auto()
    FUNCTION = auto()

    UNKNOWN = auto()

Operand_Type_Str_Map = {
    OperandType.VOID : "void",
    OperandType.VAR: "var",
    OperandType.SSA_VAR: "ssa var",
    OperandType.INT: "int",
    OperandType.FLOAT: "float",
    OperandType.BOOL: "bool",
    OperandType.STR: "str",
    OperandType.PTR: "ptr",
    OperandType.ARGS: "args",
    OperandType.UNKNOWN: "unknown",
    OperandType.FUNCTION: "function"
}

Const_Operand_Type = {
    OperandType.BOOL,
    OperandType.FLOAT,
    OperandType.INT,
    OperandType.STR
}


class Type:
    def __init__(self, name: OperandType):
        self.name = name
    def __repr__(self):
        return self.name
    def __eq__(self, other):
        self.name = other.name

    def is_void(self):
        return True if self.name == OperandType.VOID else False
    def is_const(self):
        return True if self.name in Const_Operand_Type else False
    def is_ssa_var(self) -> bool:
        return True if self.name == OperandType.SSA_VAR else False
    def is_var(self) -> bool:
        return True if self.name == OperandType.VAR else False
    def is_ptr(self) -> bool:
        return True if self.name == OperandType.PTR else False

VOID = Type(OperandType.VOID)

INT = Type(OperandType.INT)
FLOAT = Type(OperandType.FLOAT)
BOOL = Type(OperandType.BOOL)
STR = Type(OperandType.STR)

SSA_VAR = Type(OperandType.SSA_VAR)
VAR = Type(OperandType.VAR)

PTR = Type(OperandType.PTR)


class Operand:

    # ++++++++ init ++++++++
    def __init__(self, op_type: OperandType, value):
        self.type = op_type
        self.value = value

    def __eq__(self, other):
        return True if self.type == other.type \
                       and self.value == other.value else False

    def __hash__(self):
        return hash((self.type, self.value))

    # ++++++++ str ++++++++

    def __repr__(self):
        return f"[{Operand_Type_Str_Map[self.type]}]{str(self)}"

    def __str__(self):
        formatter = {
            OperandType.PTR: self._format_addr,
        }.get(self.type, self._format_const)
        return formatter()
    def _format_addr(self):
        from cof.base.mir.inst import MIRInsts
        return f"addr-{MIRInsts.insts_dict_by_id[self.value].addr}"
    def _format_const(self):
        return str(self.value)
    def _val(self, operand: 'Operand'):
        assert isinstance(self.type, OperandType)
        return "" if operand is None else str(operand)

    # ++++++++ type ++++++++
    def is_const(self) -> bool:
        return True if self.type else False
    def is_ssa_var(self) -> bool:
        return True if self.type == OperandType.SSA_VAR else False
    def is_var(self) -> bool:
        return True if self.type == OperandType.VAR else False
    def is_ptr(self) -> bool:
        return True if self.type == OperandType.PTR else False
    def is_void(self) -> bool:
        return True if self.type == OperandType.VOID else False

    # ++++++++ value ++++++++
    def is_true(self) -> bool:
        return False if self.type == OperandType.BOOL and self.value == False else True

