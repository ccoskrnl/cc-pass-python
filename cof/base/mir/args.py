from typing import List


class Args:
    def __init__(self, args: List):
        self.args = args
    def __repr__(self):
        return ', '.join(map(str, self.args))


    # def __repr__(self):
    #     return f"{self.__class__.__name__}({', '.join(map(repr, self.args))})"

