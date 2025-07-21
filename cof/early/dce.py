# Dead Code Elimination
from typing import Tuple, Dict

from cof.early.sccp import SCCPAnalyzer
from cof.ir.mir import MIRInstId, MIRInsts


def control_flow_dce(sccp_analyzer: SCCPAnalyzer) -> MIRInsts:

    exec_flow: Dict[Tuple[MIRInstId, MIRInstId], bool] = sccp_analyzer.exec_flag
    inst_succ = sccp_analyzer.fatten_blocks.succ
    original_inst = sccp_analyzer.cfg.insts.ret_insts()
    id_2_inst = sccp_analyzer.cfg.insts_dict_by_id
    dec_insts = MIRInsts(None)

    for inst in original_inst:
        for succ_id in inst_succ[inst.id]:
            if exec_flow[(inst.id, succ_id)]:
                dec_insts.insert_insts(None, inst)

    dec_insts.insert_insts(None, original_inst[-1])
    return dec_insts