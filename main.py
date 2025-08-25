from cof.local import LocalCodeOptimizer
from cof.base.cfg.visualizer import visualize_cfg
from cof.base.mir import MIRInsts
from test import testing

if __name__ == "__main__":
    insts: MIRInsts = testing()
    local_optimizer = LocalCodeOptimizer(insts=insts)
    local_optimizer.initialize()
    final_insts = local_optimizer.optimize()

    visualize_cfg(local_optimizer.cfg)
