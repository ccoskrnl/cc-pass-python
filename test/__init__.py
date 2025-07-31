from .parser import *

def testing() -> MIRInsts:
    # p = Parser("test/ssa_example.ir")
    # p = Parser("test/example.ir")
    # p = Parser("test/example_01.ir")
    p = Parser("test/sccp_example.ir")
    return p.parse()
