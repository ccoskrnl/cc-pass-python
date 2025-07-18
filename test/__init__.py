from cof.ir import *
from .parser import *

def testing() -> MIRInsts:
    # p = Parser("test/ssa_example.ir")
    p = Parser("test/example.ir")
    return p.parse()
