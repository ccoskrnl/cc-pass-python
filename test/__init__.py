from cof.ir import *
from .parser import *

def testing() -> MIRInsts:
    p = Parser("test/ssa_example.ir")
    return p.parse()
