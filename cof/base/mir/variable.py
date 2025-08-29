class Variable:
    def __init__(self, varname: str):
        self.varname = varname
        self.temporary = False
    def __repr__(self):
        return self.varname
    def __hash__(self):
        return hash(self.varname)
    def __eq__(self, other):
        return self.varname == other.varname