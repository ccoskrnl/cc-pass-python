from cof.ir import *
from .parser import *

def testing() -> Insts:
    p = Parser("test/ssa_example.ir")
    return p.parse()
