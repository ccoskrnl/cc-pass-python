from cof.base.mir.operand import Operand_Type_Str_Map, OperandType, Operand

from cof.base.mir.operator import Op


def mir_eval(op: Op, operand1: Operand, operand2: Operand) -> Operand:

    def normalize_operands(opnd1: Operand, opnd2: Operand) -> tuple:
        if opnd1.type == opnd2.type:
            return opnd1.value, opnd2.value, opnd1.type
        numeric_types = { OperandType.INT, OperandType.FLOAT }
        if opnd1.type in numeric_types and opnd2.type in numeric_types:
            # widening to float
            return float(opnd1.value), float(opnd2.value), OperandType.FLOAT

        raise TypeError("Incompatible operand types: "
                        f"{Operand_Type_Str_Map[opnd1.type]} and {Operand_Type_Str_Map[opnd2.type]}")

    def safe_divide(a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Division by zero")
        return a / b

    op1, op2, result_type = normalize_operands(operand1, operand2)

    op_handlers = {
        Op.ADD: lambda a, b: a + b,
        Op.SUB: lambda a, b: a - b,
        Op.MUL: lambda a, b: a * b,
        Op.DIV: safe_divide,
        Op.MOD: lambda a, b: a % b,
        Op.LE: lambda a, b: a < b,
        Op.GE: lambda a, b: a > b,
        Op.LEQ: lambda a, b: a <= b,
        Op.GEQ: lambda a, b: a >= b,
        Op.EQ: lambda a, b: a == b,
        Op.NEQ: lambda a, b: a != b,
    }

    if op not in op_handlers:
        return Operand(OperandType.UNKNOWN, None)

    handler = op_handlers[op]
    result_value = handler(op1, op2)

    final_type = OperandType.BOOL if op in Bool_Op else result_type

    return Operand(final_type, result_value)
