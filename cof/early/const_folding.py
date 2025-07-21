from cof.early.sccp import SCCPAnalyzer
from cof.ir.lattice import ConstLattice
from cof.ir.mir import MIRInsts, Operand, mir_eval


def constant_folding(sccp_analyzer: SCCPAnalyzer):
    insts: MIRInsts = sccp_analyzer.get_insts()
    for inst in insts.ret_insts():
        operand_var_list = inst.get_operand_list()

        for var in operand_var_list:
            if var.is_ssa_var():
                lattice: ConstLattice = sccp_analyzer.lat_cell[str(var)]
                if lattice.is_constant():
                    var.type = lattice.value.type
                    var.value = lattice.value.value

        dest_var: Operand = inst.get_dest_var()

        if inst.is_arithmetic() and inst.all_constant_operands():
            ret_val: Operand = mir_eval(inst.op, inst.operand1, inst.operand2)
            dest_var.type = ret_val.type
            dest_var.value = ret_val.value

        if inst.is_if() and dest_var.is_true():
            inst.if_to_goto()
