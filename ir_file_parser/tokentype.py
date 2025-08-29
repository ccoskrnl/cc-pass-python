from enum import Enum
import re

from cof.base.mir.operator import Op


class TokenType(Enum):

    VAR = 1

    BOOL = 10
    FLOAT = 11
    INT = 12
    STR = 13

    ARGS = 18
    PRUN = 19

    OP = 20

    ADDR = 30

    UNKNOWN = 99



KEYWORDS = {'%if', '%goto', '%entry', '%exit', '%true', '%false', '%print', '%init'}
OP_KEYWORDS = {'%if', '%goto', '%entry', '%exit', '%print', '%init'}
BOOL_TRUE_VALUE = "%true"
BOOL_FALSE_VALUE = "%false"

# C-like variable
VAR_NAME_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*')

LABEL_REF_PATTERN = re.compile(r'^&[A-Za-z_][A-Za-z0-9_]*')
LABEL_DEF_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*:')

# Not support for scientific notation
FLOAT_PATTERN = re.compile(r'^\d+(\.\d+)?$')

INT_PATTERN = re.compile(r'^\d+$')

OP_PATTERN = re.compile(r'^[+\-*/=<>!&|^%:]+$')

# parenthesis
PARENTHESIS_PATTERN = re.compile(r'^[()]$')

OP_MAP = {
    ":=": Op.ASSIGN,
    "=": Op.EQ,
    "<": Op.LE,
    ">": Op.GE,
    "<=": Op.LEQ,
    ">=": Op.GEQ,
    "!=": Op.NEQ,
    "+": Op.ADD,
    "-": Op.SUB,
    "*": Op.MUL,
    "/": Op.DIV,
    "%": Op.MOD,
    "%if": Op.IF,
    "%goto": Op.GOTO,
    "%exit": Op.EXIT,
    "%entry": Op.ENTRY,
    "%init": Op.INIT,
    "%print": Op.PRINT
}

def get_op_type(op_token: str):
    return OP_MAP.get(op_token, Op.UNKNOWN)


class Token:
    def __init__(self, token_type: TokenType, value):
        self.token_type = token_type
        self.value = value


    def is_id(self):
        if self.token_type == TokenType.VAR:
            return True
        else:
            return False

    def is_literal(self) -> bool:
        return self.token_type in {
            TokenType.BOOL,
            TokenType.FLOAT,
            TokenType.INT,
            TokenType.STR
        }

    def is_left_parenthesis(self) -> bool:
        return self.token_type == TokenType.PRUN and self.value == '('

    def is_right_parenthesis(self) -> bool:
        return self.token_type == TokenType.PRUN and self.value == ')'

    def is_value(self):
        return self.is_id() or self.is_literal()

    def is_assign(self):
        return self.token_type == TokenType.OP and self.value == Op.ASSIGN

    def is_if(self):
        return self.token_type == TokenType.OP and self.value == Op.IF

    def is_goto(self):
        return self.token_type == TokenType.OP and self.value == Op.GOTO

    def is_label(self):
        return self.token_type == TokenType.ADDR

    def is_init(self):
        return self.token_type == TokenType.OP and self.value == Op.INIT

    def is_entry(self):
        return self.token_type == TokenType.OP and self.value == Op.ENTRY

    def is_exit(self):
        return self.token_type == TokenType.OP and self.value == Op.EXIT

    def is_print(self):
        return self.token_type == TokenType.OP and self.value == Op.PRINT