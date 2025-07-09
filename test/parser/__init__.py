import re
from typing import List, Dict

from .tokentype import *
from cof.ir import Insts, IRInst, OperandType, Operand, Variable
import sys

token_type_2_operand_type: Dict[TokenType, OperandType] = {

    TokenType.ADDR: OperandType.ADDR,
    TokenType.VAR: OperandType.VAR,

    TokenType.INT: OperandType.INT,
    TokenType.FLOAT: OperandType.FLOAT,
    TokenType.BOOL: OperandType.BOOL,
    TokenType.STR: OperandType.STR,
}

def token_type_to_operand_type(token_type: TokenType) -> OperandType:
    assert token_type != TokenType.UNKNOWN
    return token_type_2_operand_type[token_type]

class Parser:
    def __init__(self, filename):
        self.labels_table = { }
        self.ir_file = filename

    def parse(self) -> Insts:
        insts = Insts()
        index = 0
        need_to_add_label = False
        label_tag: str = ""

        with open(self.ir_file, 'r', encoding="utf-8") as ir_file:
            content = ""

            for line in ir_file.read().split('\n'):
                line = line.strip()
                if line and line[0] == '#':
                    continue
                content += line + '\n'

            lines = [ ]
            for line in content.split('\n'):
                if not line:
                    continue
                if re.match(LABEL_DEF_PATTERN, line):
                    # label_tag defined by user.
                    label_tag = line.strip()[0:-1]
                    self.labels_table[label_tag] = index
                else:
                    index += 1
                    lines.append(line)

            for line in lines:
                if not re.match(LABEL_DEF_PATTERN, line):
                    insts.add_an_inst(self.generate_an_inst(line))



        return insts

    def recognize_token(self, text) -> List[Token]:
        tokens = text.split()
        token_sequence: List[Token] = [ ]

        for value in tokens:
            if value in {'entry', 'exit', 'if', 'goto', 'print'}:
                token_sequence.append(Token(TokenType.OP, get_op_type(value)))
            elif value == 'false':
                token_sequence.append(Token(TokenType.BOOL, False))
            elif value == 'true':
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
                token_sequence.append(Token(TokenType.ADDR, self.labels_table[value[1:]]))
            elif re.match(PARENTHESIS_PATTERN, value):
                token_sequence.append(Token(TokenType.PRUN, value))
            else:
                print("\nfatal error: ")
                print("Cannot recognize the token...")
                import traceback
                traceback.print_exc()

                sys.exit(-1)

        return token_sequence


    def generate_an_inst(self, text) -> IRInst:
        inst = IRInst(
            op=Op.UNKNOWN,
            operand1=None,
            operand2=None,
            result=None)

        token_seq: List[Token] = self.recognize_token(text)
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
                token_type_to_operand_type(token_seq[2].token_type)
                , token_seq[2].value
            )

            inst.operand2 = Operand(
                token_type_to_operand_type(token_seq[4].token_type)
                , token_seq[4].value
            )

            inst.result = Operand(
                token_type_to_operand_type(token_seq[0].token_type)
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
                token_type_to_operand_type(token_seq[1].token_type)
                , token_seq[1].value
            )

            inst.result = Operand(
                token_type_to_operand_type(token_seq[3].token_type)
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
                token_type_to_operand_type(token_seq[2].token_type)
                , token_seq[2].value
            )
            inst.result = Operand(
                token_type_to_operand_type(token_seq[0].token_type)
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
                token_type_to_operand_type(token_seq[1].token_type)
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
            inst.op = Op.CALL
            inst.result = Operand(
                token_type_to_operand_type(token_seq[0].token_type)
                , token_seq[0].value
            )
            inst.operand1 = Operand(
                token_type_to_operand_type(token_seq[2].token_type)
                , token_seq[2].value
            )
            args = [ ]
            for i in range(4, len(token_seq) - 1):
                args.append(Operand(
                    token_type_to_operand_type(token_seq[i].token_type)
                    , token_seq[i].value
                ))
            inst.operand2 = Operand(OperandType.ARGS, args)

        # phi ( v1 v2 v3 )
        elif (
            token_seq[0].is_id()
            and token_seq[1].is_left_parenthesis()
            and token_seq[-1].is_right_parenthesis()
        ):
            inst.op = Op.CALL
            inst.operand1 = Operand(
                token_type_to_operand_type(token_seq[0].token_type)
                , token_seq[0].value
            )
            args = [ ]
            for i in range(2, len(token_seq) - 1):
                args.append(Operand(
                    token_type_to_operand_type(token_seq[i].token_type)
                    , token_seq[i].value
                ))
            inst.operand2 = Operand(OperandType.ARGS, args)

        # print operand
        elif (
            len(token_seq) == 2
            and (token_seq[0].is_print() or token_seq[1].is_value())
        ):
            inst.op = Op.PRINT
            inst.operand1 = Operand(
                token_type_to_operand_type(token_seq[1].token_type)
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