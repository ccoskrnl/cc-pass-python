from cof.local import LocalCodeOptimizer
from cof.cfg.visualizer import visualize_cfg
from cof.ir.mir import MIRInsts
from test import testing

if __name__ == "__main__":
    insts: MIRInsts = testing()
    optimizer = LocalCodeOptimizer(insts=insts)
    optimizer.initialize()
    optimizer.optimize()
    visualize_cfg(optimizer.cfg)