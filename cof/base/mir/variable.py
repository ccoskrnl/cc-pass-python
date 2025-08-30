from enum import Enum, auto


class VariableScope(Enum):
    Global = auto()
    Local = auto()

class Variable:
    def __init__(
            self,
            varname: str,
            scope: VariableScope = VariableScope.Local,
            compiler_generated: bool = False
    ):
        self.varname: str = varname
        self.scope: VariableScope = scope
        self.compiler_generated: bool = compiler_generated

    def __repr__(self):
        return self.varname
    def __hash__(self):
        return hash((self.varname, self.scope, self.compiler_generated))
    def __eq__(self, other):
        return self.varname == other.varname \
                and self.scope == other.scope \
                and self.compiler_generated == other.compiler_generated