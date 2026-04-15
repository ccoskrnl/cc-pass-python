from pathlib import Path
from typing import List, Tuple

from cof import LocalCodeOptimizer, CodeOptimizer
from cof.analysis.dataflow import DataFlowAnalyzer
from cof.base.cfg import ControlFlowGraph
from cof.base.mir.function import MIRFunction
from cof.base.mir.inst import MIRInsts
from ir_file_parser import Parser
from utils.cfg_visualizer import visualize_cfg


def testing(ir_path) -> Tuple[MIRInsts, List[MIRFunction]]:
    p = Parser(ir_path)
    p.parse()
    p.insts.assign_addr()
    return p.insts, p.func_list


# ++++++++ Output ++++++++
def output_mir(insts, output_file):

    output_path = Path(output_file)
    output_dir = output_path.parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, mode='w', encoding='utf-8') as file:
        file.write(str(insts))


if __name__ == "__main__":
    mir, mir_func = testing("ir_examples/reaching_defs_example.ir")
    cfg = ControlFlowGraph(mir_func[0].insts)
    dfa = DataFlowAnalyzer(cfg=cfg)
    dfa.reaching_definitions()
