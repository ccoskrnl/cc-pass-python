from typing import Optional, List, Callable, Any, Union, Dict

from cof.base.mir.operand import Operand, OperandType, Const_Operand_Type
from cof.base.mir.operator import Op, op_str, Evaluatable_Op, Arithmetic_Op, Assignment_Op, Expression_Op
from cof.base.mir.variable import Variable



# ++++++++++++++++++++++++ MIR ++++++++++++++++++++

type MIRInstId = int
type MIRInstAddr = int

mir_inst_id = 0
def new_id() -> MIRInstId:
    global mir_inst_id
    mir_inst_id += 1
    return mir_inst_id

def _val(value) -> str:
    return str(value) if value else ""

class MIRInst:
    """

    if cond goto dest_addr
        inst.op = Op.IF
        inst.operand1 = Operand(cond)
        inst.result = Operand(dest_addr)

    retval := callee( arg1, arg2 )
        inst.op = Op.CALL_ASSIGN
        inst.operand1 = Operand(callee)
        inst.operand2 = Operand(Arg( arg1, arg 2))
        inst.result = Operand(retval)

    callee( arg1, arg 2)
        inst.op = Op.CALL
        inst.operand1 = Operand(callee)
        inst.operand2 = Operand(Arg( arg1, arg 2))

    """
    def __init__(self, offset, op, operand1, operand2, result):
        self.unique_id: MIRInstId = new_id()
        # self.id: MIRInstId = 0
        self.addr: MIRInstAddr = 0
        self.offset: MIRInstAddr = offset
        self.op = op
        self.operand1: Operand = operand1
        self.operand2: Optional[Operand] = operand2
        self.result: Optional[Operand] = result
    def __hash__(self):
        return hash(self.unique_id)
    def __eq__(self, other):
        # if not isinstance(other, MIRInst):
        #     return False
        return self.unique_id == other.unique_id

    def __str__(self):
        formatter = {
            Op.IF: self._format_branch,
            Op.GOTO: self._format_jump,
            Op.ASSIGN: self._format_assign,
            Op.ENTRY: self._format_entry_exit,
            Op.EXIT: self._format_entry_exit,
            Op.PRINT: self._format_print,
            Op.CALL: self._format_call,
            Op.PHI: self._format_phi,
            Op.INIT: self._format_init,
            Op.FUNCTION_DEF: self._format_func,
        }.get(self.op, self._format_operator)

        # return formatter()
        return f"[addr:{self.addr:>{4}}]    {formatter()}"

    # def __repr__(self):
    #     return f"[addr:{self.addr:>{4}}]    {str(self)}"

    def _format_init(self):
        return f"%init {_val(self.result)}"
    def _format_branch(self):
        return f"%if {_val(self.operand1)} %goto {_val(self.result)}"
    def _format_jump(self):
        return f"%goto {_val(self.result)}"
    def _format_assign(self):
        return f"{_val(self.result)} := {_val(self.operand1)}"
    def _format_entry_exit(self):
        return op_str(self.op)
    def _format_print(self):
        return f"%print {_val(self.operand1)}"
    def _format_operator(self):
        op_symbol = op_str(self.op)
        return (
            f"{_val(self.result)} := "
            f"{_val(self.operand1)} "
            f"{op_symbol} {_val(self.operand2)}"
        )
    def _format_call(self):
        if self.result:
            return (
                f"{_val(self.result)} := "
                f"{_val(self.operand1)}("
                f"{_val(self.operand2)})"
            )
        else:
            return (
                f"{_val(self.operand1)}("
                f"{_val(self.operand2)})"
            )
    def _format_phi(self):
        return (
            f"{_val(self.result)} := "
            f"{_val(self.operand1)}("
            f"{_val(self.operand2)})"
        )
    def _format_func(self):
        return str(self.operand1.value)

    def is_evaluatable(self) -> bool:
        return True if self.op in Evaluatable_Op else False
    def is_arithmetic(self) -> bool:
        return True if self.op in Arithmetic_Op else False
    def is_assignment(self) -> bool:
        return True if self.op in Assignment_Op else False
    def is_exp(self) -> bool:
        return True if self.op in Expression_Op else False
    def is_if(self) -> bool:
        return True if self.op == Op.IF else False
    def is_goto(self) -> bool:
        return True if self.op == Op.GOTO else False
    def is_call(self) -> bool:
        return True if self.op == Op.CALL or self.op == Op.CALL_ASSIGN else False
    def is_phi(self) -> bool:
        return True if self.op == Op.PHI else False
    def is_init(self) -> bool:
        return True if self.op == Op.INIT else False
    def is_func(self) -> bool:
        return True if self.op == Op.FUNCTION_DEF else False


    def ret_dest_variable(self) -> Optional[Operand]:
        """
        Retrieve the destination variable of the instruction.
        1. Return the assigned variable if it is an assignment instruction.
        2. Return the condition operand if it is a condition branch instruction.
        3. Return None if it is not one of the two type instructions above.
        """
        # assert self.result.type == OperandType.VAR
        if self.op in Assignment_Op:
            assert self.result
            return self.result
            # return self.result.value if self.result else None
        elif self.is_if():
            assert self.operand1
            return self.operand1
        return None

    def ret_assigned_var(self) -> Optional[Variable]:
        """
        Retrieve the assigned variable of the assignment instruction.
        """
        if self.is_assignment():
            assert self.result
            return self.result.value
        return None

    def ret_a_operand_list_for_evaluatable_exp_inst(self) -> List[Operand]:
        """
        Return an operand list for an evaluatable expression instruction.
        1. Add operands into the list if the instruction is a binary expression.
        2. Add condition operand into the list if the instruction is a condition branch.
        """
        if self.is_exp():
            return [self.operand1, self.operand2] if self.operand2 else [self.operand1]
        elif self.is_if():
            return [self.operand1]
        return []

    def ret_call_args_list(self) -> List[Operand]:
        """
        Return an arguments list for call instruction.
        You need to identify the instruction is call instruction before you call this method.
        """
        assert self.op == Op.CALL or self.op == Op.PHI or self.op == Op.CALL_ASSIGN
        assert self.operand2.type == OperandType.ARGS
        return self.operand2.value.args

    def ret_operand_list(self) -> List[Operand]:
        """
        Return an operand list for evaluatable instructions (include call instruction, but exclude goto )
        """
        l: List[Operand] = []

        if self.is_phi():
            l = self.ret_call_args_list()

        elif self.is_call():
            l = self.ret_call_args_list()

        elif self.is_exp():
            l.append(self.operand1)
            if self.operand2:
                l.append(self.operand2)

        elif self.is_if():
            l.append(self.operand1)

        return l

    def all_constant_operands(self):
        """
        check if all operands is constant, otherwise return false.
        """
        for operand in self.ret_a_operand_list_for_evaluatable_exp_inst():
            if operand.type not in Const_Operand_Type:
                return False
        return True


    def convert_if_to_goto(self):
        assert self.is_if()
        self.op = Op.GOTO
        self.operand1 = None
        self.operand2 = None



class MIRInsts:

    # global_insts_dict_by_id: Dict[MIRInstId, MIRInst] = { }
    insts_dict_by_id: Dict[MIRInstId, MIRInst] = { }

    def __init__(self, insts:Optional[List[MIRInst]]=None):

        self.ir_insts: List[MIRInst] = []
        self.num: int = 0
        # self.insts_dict_by_id: Dict[MIRInstId, MIRInst] = { }
        self.phi_insts_idx_end: int = 0

        self._initialize(insts)

    def _initialize(self, insts):
        if insts:
            self.ir_insts = insts
            self.insts_dict_by_id = {inst.unique_id: inst for inst in insts}
            self.num = len(insts)


    def __str__(self):
        return "\n".join(map(str, self.ir_insts))

    def assign_addr(self, base: int = 0) -> int:
        for i in self.ir_insts:
            i.addr = base
            if i.op == Op.FUNCTION_DEF:
                func_code: 'MIRInsts' = i.operand1.value.insts
                base = func_code.assign_addr(base=base)


            base += 1

        return base



    # def __repr__(self):
    #     return "\n".join(map(str, self.ir_insts))

    # def inst_exist(self, inst: MIRInst) -> bool:
    #     for i in self.ret_insts():
    #         if i == inst:
    #             return True
    #     return False
    def inst_exist(self, predicate: Callable[[MIRInst], bool]) -> bool:
        for inst in self.ir_insts:
            if predicate(inst):
                return True
        return False

    def inst_exist_by_key(self, *, key: str, value: Any) -> bool:
        for inst in self.ir_insts:
            if getattr(inst, key) == value:
                return True
        return False

    def inst_exist_by_id(self, inst_id: int) -> bool:
        result =  self.insts_dict_by_id.get(inst_id, False)
        if result is not False:
            return True
        else:
            return False

    def inst_exist_by_addr(self, addr: int) -> bool:
        for inst in self.ret_insts():
            if inst.offset == addr:
                return True
        return False

    def add_phi_inst(self, phi_inst: MIRInst) -> None:
        self.ir_insts.insert(0, phi_inst)
        self.phi_insts_idx_end += 1
        self.insts_dict_by_id[phi_inst.unique_id] = phi_inst

    def insert_insts(self, insts: Union[MIRInst, List[MIRInst]], index: Optional[int] = None) -> None:

        if index is None or index >= self.num:
            index = self.num

        if isinstance(insts, MIRInst):
            self.ir_insts.insert(index, insts)
            self.insts_dict_by_id[insts.unique_id] = insts
            self.num += 1

        elif isinstance(insts, List) and all(isinstance(item, MIRInst) for item in insts):
            self.ir_insts[index:index] = insts
            self.num += len(insts)
            for i in insts:
                self.insts_dict_by_id[i.unique_id] = i

    def inst_by_id(self, inst_id: MIRInstId) -> Optional[MIRInst]:
        dest_inst = self.insts_dict_by_id.get(inst_id, None)
        # if dest_inst is None:
        #     for inst in self.ir_insts:
        #         if inst.op == Op.FUNCTION_DEF:
        #             func = inst.operand1.value
        #             dest_inst = func.insts.inst_by_id(inst_id)
        return dest_inst

    def find_inst_by_key(self, *, key: str, value: Any) -> Optional[MIRInst]:
        for inst in self.ir_insts:
            if getattr(inst, key) == value:
                return inst
        return None

    # find_inst(lambda i: i.addr == 0x1000)
    def find_inst(self, predicate: Callable[[MIRInst], bool]) -> Optional[MIRInst]:
        for inst in self.ir_insts:
            if predicate(inst):
                return inst
        return None

    def index_for_inst(self, inst: MIRInst) -> int:
        return self.ir_insts.index(inst)


    def ret_inst_by_idx(self, index: int) -> MIRInst:
        return self.ir_insts[index]
    def ret_insts_by_pos(self, start_pos: int, end_pos: int) -> List[MIRInst]:
        return self.ir_insts[start_pos:end_pos]
    def ret_insts(self) -> List[MIRInst]:
        return self.ir_insts
    def ret_phi_insts(self) -> List[MIRInst]:
        return self.ir_insts[: self.phi_insts_idx_end]
    def ret_ordinary_insts(self) -> List[MIRInst]:
        return self.ir_insts[self.phi_insts_idx_end:]

    def highset_addr(self) -> int:
        return self.ir_insts[-1].offset

    def print(self):
        for inst in self.ir_insts:
            print(inst)
