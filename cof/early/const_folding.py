from cof.early.sccp import SCCPAnalyzer
from cof.ir.lattice import ConstLattice
from cof.ir.mir import MIRInsts, Operand, mir_eval


def constant_folding(sccp_analyzer: SCCPAnalyzer):
    insts: MIRInsts = sccp_analyzer.get_insts()
    for inst in insts.ret_insts():
        dest_var_list = inst.get_operand_list()
        for var in dest_var_list:
            if var.is_ssa_var():
                lattice: ConstLattice = sccp_analyzer.lat_cell[str(var)]
                if lattice.is_constant():
                    var.type = lattice.value.type
                    var.value = lattice.value.value

        if inst.is_arithmetic() and inst.all_constant_operands():
            ret_val: Operand = mir_eval(inst.op, inst.operand1, inst.operand2)
            inst.result.type = ret_val.type
            inst.result.value = ret_val.value