from cof.cfg import ControlFlowGraph
from cof.local import LocalCodeOptimizer
from cof.cfg.visualizer import visualize_cfg
from cof.ir.mir import MIRInsts
from test import testing

if __name__ == "__main__":
    insts: MIRInsts = testing()
    local_optimizer = LocalCodeOptimizer(insts=insts)
    local_optimizer.initialize()
    final_insts = local_optimizer.optimize()
    # final_insts.print()
    # final_cfg = ControlFlowGraph(final_insts)
    # visualize_cfg(final_cfg)

    visualize_cfg(local_optimizer.cfg)
