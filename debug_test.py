from pathlib import Path
from typing import List, Tuple

from cof import LocalCodeOptimizer, CodeOptimizer
from cof.base.cfg import ControlFlowGraph
from cof.base.mir.function import MIRFunction
from cof.base.mir.inst import MIRInsts
from ir_file_parser import Parser
from utils.cfg_visualizer import visualize_cfg


def testing() -> Tuple[MIRInsts, List[MIRFunction]]:
    # p = Parser("ir_examples/example1.ir")
    p = Parser("ir_examples/sccp_example.ir")
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
    global_insts, func_list = testing()

    print(global_insts)
    opter = CodeOptimizer(global_insts, func_list, sccp_enable=True, pre_algorithm='', ssa_period='always')
    opter.optimize()
    print(global_insts)

    # func = func_list[0]
    # cfg = ControlFlowGraph(func.insts)
    # lco = LocalCodeOptimizer(cfg, sccp_enable=False, pre_algorithm='', ssa_period='always')
    # lco.initialize()
    # lco.optimize()
    # print(global_insts)
    # visualize_cfg(cfg)
    # output_mir(global_insts, "ir_examples/output/opt_example1.ir")

