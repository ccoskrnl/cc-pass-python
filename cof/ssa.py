from .cfg.bb import BasicBlock
from .ir import *

class SSAVariable:

    __slots__ = ('name', 'version')
    def __init__(self, var: Union[str, Variable], version: Optional[int]):
        self.name = var.varname if isinstance(var, Variable) else var
        self.version = version if version is not None else -1

    def __str__(self):
        return f"{self.name}-{self.version}"

    @property
    def base_name(self) -> str:
        return self.name

class SSAEdge:
    __slots__ = ('source', 'target', 'var')
    def __init__(self, source, target, var):
        self.source = source
        self.target = target
        self.var = var

class SSAEdgeBuilder:
    def __init__(self, cfg):
        self.cfg = cfg
        self.edges = [ ]
        self.def_map = { }

def create_phi_function(varname: str, num_pred_s: int) -> MIRInst:
    args: List[Operand] = []
    for i in range(0, num_pred_s):
        args.append(Operand(OperandType.SSA_VAR, SSAVariable(varname, None)))

    return MIRInst(
        addr=-1,
        op=Op.PHI,
        operand1=Operand(OperandType.VAR, Variable("φ")),
        operand2=Operand(OperandType.ARGS, Args(args)),
        result = Operand(OperandType.SSA_VAR, SSAVariable(varname, None)),
    )

def has_phi_for_var(block: BasicBlock, varname: str):
    # iterate all insts
    for phi_inst in block.insts.ret_phi_insts():
        result: SSAVariable = phi_inst.result.value
        if result.base_name == varname:
            return True
    return False

