from enum import Enum, auto

LCM_TMP_VAR_PREFIX = "lcm_tv"
PHI_TMP_VAR_PREFIX = "phi_tv"

class VariableScope(Enum):
    Global = auto()
    Local = auto()

class Variable:

    __slots__ = ('varname', 'scope', 'compiler_generated')

    def __init__(
            self,
            varname: str,
            scope: VariableScope = VariableScope.Local,
            compiler_generated: bool = False
    ):
        self.varname: str = varname
        self.scope: VariableScope = scope
        self.compiler_generated: bool = compiler_generated

    @property
    def base_name(self) -> str:
        return self.varname

    def __repr__(self):
        return self.varname
    def __hash__(self):
        return hash((self.varname, self.scope, self.compiler_generated))
    def __eq__(self, other : 'Variable'):
        return self.varname == other.varname \
                and self.scope == other.scope \
                and self.compiler_generated == other.compiler_generated