from cof.base.mir.inst import MIRInsts
from cof.base.mir.operand import OperandType
from cof.base.mir.variable import Variable, VariableScope


class MIRFunction:
    def __init__(self, func_name: str, args: list):
        self.insts: MIRInsts = MIRInsts()
        self.func_name: str = func_name
        self.type: OperandType = OperandType.FUNCTION
        self.args: list = [ ]
        self._read_args(args)

    def _read_args(self, args: list):
        for a in args:
            new_var = Variable(a, VariableScope.Local)
            self.args.append(new_var)

    def __eq__(self, other):
        return self.func_name == other.func_name and self.args == self.args

    def __hash__(self):
        return hash((self.func_name, self.type))

    def __repr__(self):
        return f"@function {self.func_name} ( {" ".join(map(str, self.args)) } )\n"

    def __str__(self):
        return f"@function {self.func_name} ( {" ".join(map(str, self.args)) } )\n\t" \
            + "\n\t".join(map(str, self.insts.ret_insts())) \
            + "\n@end function\n"