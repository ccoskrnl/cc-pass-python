from typing import Dict, List, Tuple

from cof.analysis.ssa import SSAEdgeBuilder, SSAVariable
from cof.cfg import ControlFlowGraph, BasicBlockId
from cof.ir.lattice import ConstLattice
from cof.ir.mir import MIRInstId




class SCCPOptimizer:
    def __init__(self, cfg: ControlFlowGraph, ssa_builder: SSAEdgeBuilder):
        self.cfg: ControlFlowGraph = cfg
        self.ssa_builder: SSAEdgeBuilder = ssa_builder

        # exec_flag[(a, b)] records whether flowgraph edge a -> b is executable.
        self.exec_flag: Dict[Tuple[BasicBlockId, BasicBlockId], bool] = { }
        # lat_cell[ssa_v] records ConstLattice which relates ssa_v in the exit
        # of the node defined SSAVariable ssa_v
        self.lat_cell: Dict[SSAVariable, ConstLattice] = { }

        self.flow_wl: List[Tuple[BasicBlockId, BasicBlockId]] = cfg.edges
        self.ssa_wl: List[Tuple[MIRInstId, MIRInstId]] = ssa_builder.edges

    # def _initialize(self):


    # helper
    def edge_count(self, b: BasicBlockId, edges: List[Tuple[BasicBlockId, BasicBlockId]]) -> int:
        """
        return number of executable flowgraph edges leading to b

        :param b:
        :param edges:
        :return:
        """
        i: int = 0
        for e in edges:
            if e[1] == b and self.exec_flag[e]:
                i += 1

        return i
