from cof.local import LocalCodeOptimizer
from cof.base.mir.inst import MIRInsts
from ir_file_parser import Parser


def testing() -> MIRInsts:
    p = Parser("ir_examples/anticipated_exprs_example.ir")
    return p.parse()


if __name__ == "__main__":
    insts: MIRInsts = testing()
    local_optimizer = LocalCodeOptimizer(insts=insts)
    local_optimizer.initialize()
    final_insts = local_optimizer.optimize()

