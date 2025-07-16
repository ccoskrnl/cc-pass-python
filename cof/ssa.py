from .cfg.bb import BasicBlock
from .ir import *

class SSAVariable(Variable):
    def __init__(self, variable):
        self.__dict__ == variable.__dict__
        # original variable name
        self.version = 0

    def __str__(self):
        return f"{self.varname}-{self.version}"

class SSAEdge:
    def __init__(self, source: BasicBlock, dest: BasicBlock, ssa_var: SSAVariable):
        self.source: BasicBlock = source
        self.dest: BasicBlock = dest
        self.ssa_var: SSAVariable = ssa_var

class SSAEdgeBuilder:
    def __init__(self, cfg):
        self.cfg = cfg
        self.edges = [ ]
        self.def_map = { }

def create_phi_function(varname: str, num_pred_s: int) -> MIRInst:
    # create argument list: [undef] * num_predecease
    args: List[Operand] = []
    for i in range(0, num_pred_s):
        args.append(Operand(OperandType.VAR, Variable(varname + '?')))

    return MIRInst(
        addr=-1,
        op=Op.PHI,
        operand1=Operand(OperandType.VAR, Variable("φ")),
        operand2=Operand(OperandType.ARGS, Args(args)),
        result = Operand(OperandType.VAR, Variable(varname)),
    )

def has_phi_for_var(block: BasicBlock, varname: str):
    # iterate all insts
    for inst in block.insts.ret_phi_insts():
        if inst.result.value.varname == varname:
            return True
    return False

