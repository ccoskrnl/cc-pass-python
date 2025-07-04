from cof.ir import *
from .parser import *

def testing() -> Insts:
    p = Parser("test/example.ir")
    return p.parse()
