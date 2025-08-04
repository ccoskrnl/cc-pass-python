from collections import defaultdict
from typing import Dict, List

from cof.analysis.dataflow.framework import DataFlowAnalysisFramework
from cof.analysis.dataflow.reaching_defs import Definition, ReachingDefLattice, ReachingDefTransfer, on_state_change
from cof.base.bb import BasicBlock
from cof.base.cfg import ControlFlowGraphForDataFlowAnalysis


class DataFlowAnalyzer:
    def __init__(self, cfg: ControlFlowGraphForDataFlowAnalysis):
        self.cfg = cfg

    def reaching_definitions(self):

        defs_dict_by_block: Dict[BasicBlock, set[Definition]] = defaultdict(set)
        for definition, block in self.cfg.collect_definitions().items():
            defs_dict_by_block[block].add(Definition(definition[0], definition[1]))

        all_defs: set[Definition] = set(List[defs_dict_by_block.values()])
        lattice = ReachingDefLattice(all_defs)
        transfer = ReachingDefTransfer(defs_dict_by_block)
        analysis = DataFlowAnalysisFramework(
            cfg=self.cfg,
            lattice=lattice,
            transfer=transfer,
            direction='forward',
            init_value=set(),
            safe_value=set(),
            on_state_change=on_state_change
        )

        analysis.analyze(strategy='worklist')

        pass