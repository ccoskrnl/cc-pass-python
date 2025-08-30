import sys
from typing import List, Dict

from cof.base.mir.args import Args
from cof.base.mir.function import MIRFunction
from cof.base.mir.inst import MIRInsts, MIRInst
from cof.base.mir.operand import OperandType, Operand
from cof.base.mir.variable import Variable
from .tokentype import *

token_type_2_operand_type: Dict[TokenType, OperandType] = {

    TokenType.ADDR: OperandType.PTR,
    TokenType.VAR: OperandType.VAR,

    TokenType.INT: OperandType.INT,
    TokenType.FLOAT: OperandType.FLOAT,
    TokenType.BOOL: OperandType.BOOL,
    TokenType.STR: OperandType.STR,
}


def _token_type_to_operand_type(token_type: TokenType) -> OperandType:
    assert token_type != TokenType.UNKNOWN
    return token_type_2_operand_type[token_type]


def _recognize_token(text) -> List[Token]:
    tokens = text.split()
    token_sequence: List[Token] = [ ]

    for value in tokens:
        if value in OP_KEYWORDS:
            token_sequence.append(Token(TokenType.OP, get_op_type(value)))
        elif value == BOOL_FALSE_VALUE:
            token_sequence.append(Token(TokenType.BOOL, False))
        elif value == BOOL_TRUE_VALUE:
            token_sequence.append(Token(TokenType.BOOL, True))
        elif re.match(OP_PATTERN, value):
            token_sequence.append(Token(TokenType.OP, get_op_type(value)))
        elif re.match(VAR_NAME_PATTERN, value):
            token_sequence.append(Token(TokenType.VAR, Variable(value)))
        elif re.match(INT_PATTERN, value):
            try:
                num = int(value)
                token_sequence.append(Token(TokenType.INT, num))
            except ValueError as e:
                print("\nfatal error: ")
                # print(f"error processing value on line {current_line} ")
                print(f"value: '{value}' cannot be converted to an integer")
                print(f"error type: {type(e).__name__}")
                print(f"details: {str(e)}")

                import traceback
                traceback.print_exc()

                sys.exit(-1)
        elif re.match(FLOAT_PATTERN, value):
            try:
                num = float(value)
                token_sequence.append(Token(TokenType.FLOAT, num))
            except ValueError as e:
                print("\nfatal error: ")
                # print(f"error processing value on line {current_line} ")
                print(f"value: '{value}' cannot be converted to an float")
                print(f"error type: {type(e).__name__}")
                print(f"details: {str(e)}")

                import traceback
                traceback.print_exc()

                sys.exit(-1)
        elif re.match(LABEL_REF_PATTERN, value):
            # token_sequence.append(Token(TokenType.ADDR, self.labels_table[value[1:]]))
            token_sequence.append(Token(TokenType.ADDR, value[1:]))

        elif re.match(PARENTHESIS_PATTERN, value):
            token_sequence.append(Token(TokenType.PRUN, value))
        else:
            print("\nfatal error: ")
            print("Cannot recognize the token...")
            import traceback
            traceback.print_exc()

            sys.exit(-1)

    return token_sequence


class Parser:
    counter = 0
    def __init__(self, filename):
        self.labels_table = { }
        self.ir_file = filename
        self.insts: MIRInsts = MIRInsts()
        self.func_list: List[MIRFunction] = [ ]

    def _ignore_comments(self) -> List[str]:
        lines = [ ]
        with open(self.ir_file, 'r', encoding="utf-8") as ir_file:
            # ignore comments
            for line in ir_file.read().split('\n'):
                line = line.strip()
                if line and line[0] == '#' or not line:
                    continue
                lines.append(line)
        return lines

    def _handle_branch_jump(self, insts):
        for inst in insts.ret_insts():
            if inst.is_func():
                func: MIRFunction = inst.operand1.value
                func_insts = func.insts
                self._handle_branch_jump(func_insts)
            elif inst.is_if():
                inst.result.value = self.labels_table[inst.result.value]
            elif inst.is_goto():
                inst.result.value = self.labels_table[inst.result.value]

    def parse(self):
        lines = self._ignore_comments()
        num_of_lines = len(lines)
        i_for_lines = 0

        while i_for_lines < num_of_lines:

            func_def_match = re.match(FUNCTION_DEF_PATTERN, lines[i_for_lines])

            if not re.match(LABEL_DEF_PATTERN, lines[i_for_lines]) and not func_def_match:
                self.insts.insert_insts(self._generate_an_inst(lines[i_for_lines]))

            if func_def_match:

                function_name = func_def_match.group(1)
                args_list = [arg.strip() for arg in func_def_match.group(2).split() if arg.strip()]
                func = MIRFunction(function_name, args_list)
                self.func_list.append(func)
                self.insts.insert_insts(MIRInst(
                    self.counter,
                    op=Op.FUNCTION_DEF,
                    operand1=Operand(OperandType.FUNCTION, func),
                    operand2=None,
                    result=None))

                func_code = [ ]
                i_for_lines += 1
                while i_for_lines < num_of_lines and not re.match(FUNCTION_END_PATTERN, lines[i_for_lines]):
                    func_code.append(lines[i_for_lines])
                    i_for_lines += 1

                if i_for_lines >= num_of_lines:
                    raise "fatal: syntax error"

                self._parse_a_function(func_code, func)

            i_for_lines += 1

        self._handle_branch_jump(self.insts)

    def _generate_an_inst(self, text, label:str = None) -> MIRInst:

        inst = MIRInst(
            offset=self.counter,
            op=Op.UNKNOWN,
            operand1=None,
            operand2=None,
            result=None)
        self.counter += 1

        if label is not None:
            self.labels_table[label] = inst.unique_id


        token_seq: List[Token] = _recognize_token(text)
        # result := operand1 Op operand2
        if (
            len(token_seq) == 5
            and token_seq[0].is_id()
            and token_seq[1].is_assign()
            and (token_seq[2].is_id() or token_seq[2].is_literal())
            and (not token_seq[3].is_assign())
            and (token_seq[4].is_id() or token_seq[4].is_literal())
        ):
            inst.op = token_seq[3].value

            inst.operand1 = Operand(
                _token_type_to_operand_type(token_seq[2].token_type)
                , token_seq[2].value
            )

            inst.operand2 = Operand(
                _token_type_to_operand_type(token_seq[4].token_type)
                , token_seq[4].value
            )

            inst.result = Operand(
                _token_type_to_operand_type(token_seq[0].token_type)
                , token_seq[0].value
            )

        # if operand goto Label
        elif (
            len(token_seq) == 4
            and token_seq[0].is_if()
            and token_seq[1].is_value()
            and token_seq[2].is_goto()
            and token_seq[3].is_label()
        ):
            inst.op = Op.IF
            inst.operand1 = Operand(
                _token_type_to_operand_type(token_seq[1].token_type)
                , token_seq[1].value
            )

            inst.result = Operand(
                _token_type_to_operand_type(token_seq[3].token_type)
                , token_seq[3].value
            )

        # result := var
        elif (
            len(token_seq) == 3
            and token_seq[0].is_id()
            and token_seq[1].is_assign()
            and token_seq[2].is_value()
        ):
            inst.op = Op.ASSIGN
            inst.operand1 = Operand(
                _token_type_to_operand_type(token_seq[2].token_type)
                , token_seq[2].value
            )
            inst.result = Operand(
                _token_type_to_operand_type(token_seq[0].token_type)
                , token_seq[0].value
            )

        # goto Label
        elif (
            len(token_seq) == 2
            and token_seq[0].is_goto()
            and token_seq[1].is_label()
        ):
            inst.op = Op.GOTO
            inst.result = Operand(
                _token_type_to_operand_type(token_seq[1].token_type)
                , token_seq[1].value
            )

        # m = max ( a 4 )
        elif (
            token_seq[0].is_id()
            and token_seq[1].is_assign()
            and token_seq[2].is_id()
            and token_seq[3].is_left_parenthesis()
            and token_seq[-1].is_right_parenthesis()
        ):
            inst.op = Op.CALL_ASSIGN
            inst.result = Operand(
                _token_type_to_operand_type(token_seq[0].token_type)
                , token_seq[0].value
            )
            inst.operand1 = Operand(
                _token_type_to_operand_type(token_seq[2].token_type)
                , token_seq[2].value
            )
            args = [ ]
            for i in range(4, len(token_seq) - 1):
                args.append(Operand(
                    _token_type_to_operand_type(token_seq[i].token_type)
                    , token_seq[i].value
                ))
            inst.operand2 = Operand(OperandType.ARGS, Args(args))

        # phi ( v1 v2 v3 )
        elif (
            token_seq[0].is_id()
            and token_seq[1].is_left_parenthesis()
            and token_seq[-1].is_right_parenthesis()
        ):
            inst.op = Op.CALL
            inst.operand1 = Operand(
                _token_type_to_operand_type(token_seq[0].token_type)
                , token_seq[0].value
            )
            args = [ ]
            for i in range(2, len(token_seq) - 1):
                args.append(Operand(
                    _token_type_to_operand_type(token_seq[i].token_type)
                    , token_seq[i].value
                ))
            inst.operand2 = Operand(OperandType.ARGS, Args(args))

        # print operand
        elif (
            len(token_seq) == 2
            and (token_seq[0].is_print() and token_seq[1].is_value())
        ):
            inst.op = Op.PRINT
            inst.operand1 = Operand(
                _token_type_to_operand_type(token_seq[1].token_type)
                , token_seq[1].value
            )

        # init operand
        elif (
            len(token_seq) == 2
            and (token_seq[0].is_init() and token_seq[1].is_value())
        ):
            inst.op = Op.INIT
            inst.result = Operand(
                _token_type_to_operand_type(token_seq[1].token_type)
                , token_seq[1].value
            )


        # entry/exit
        elif (
            len(token_seq) == 1
            and (token_seq[0].is_entry() or token_seq[0].is_exit())
        ):
            inst.op = token_seq[0].value

        else:
            print("\nfatal error: ")
            print("unsupported syntax...")
            import traceback
            traceback.print_exc()

            sys.exit(-1)

        return inst

    def _parse_a_function(self, local_code: List[str], func: MIRFunction):

        label = None
        for line in local_code:
            if not re.match(LABEL_DEF_PATTERN, line):
                inst = self._generate_an_inst(line, label)
                # self.insts.insert_insts(inst)
                func.insts.insert_insts(inst)
                if label is not None:
                    label = None
            else:
                label = line[:-1]
                continue

