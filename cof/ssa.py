from .ir import *

class SSAVariable:
    def __init__(self, name, version=0):
        # original variable name
        self.name = name

        self.version = version
    def __str__(self):
        return f"{self.name}-{self.version}"

    @classmethod
    def from_string(cls, s: str):
        if '_' in s:
            name, ver = s.rsplit('-', 1)
            return cls(name, int(ver))
        return cls(s)


def create_phi_function(varname: str, num_pred_s: int):
    # create argument list: [undef] * num_predecease
    args: List[Operand] = []
    for i in range(0, num_pred_s):
        args.append(Operand(OperandType.VAR, Variable(varname + '?')))

    return IRInst(
        op=Op.CALL,
        operand1=Operand(OperandType.VAR, Variable("φ")),
        operand2=Operand(OperandType.ARGS, Args(args)),
        result = Operand(OperandType.VAR, Variable(varname)),
    )

