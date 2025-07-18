from cof import CodeOptimizer
from cof.ir.mir import MIRInsts
from test import testing

if __name__ == "__main__":
    insts: MIRInsts = testing()
    optimizer = CodeOptimizer(insts=insts)
    optimizer.initialize_optimizer()
    optimizer.visualize_cfg()