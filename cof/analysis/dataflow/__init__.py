from collections import defaultdict
from typing import Dict, List

from cof.analysis.dataflow.framework import DataFlowAnalysisFramework
from cof.analysis.dataflow.live_vars import LiveVarsLattice, LiveVarsTransfer, live_vars_on_state_change
from cof.analysis.dataflow.reaching_defs import Definition, ReachingDefLattice, ReachingDefTransfer, reaching_defs_on_state_change
from cof.base.bb import BasicBlock
from cof.base.cfg import ControlFlowGraphForDataFlowAnalysis
from cof.base.mir import Variable


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
            on_state_change=reaching_defs_on_state_change
        )

        analysis.analyze(strategy='worklist')

    def live_vars(self):
        use_dict, def_dict = self.cfg.collect_use_def()
        all_vars: set[Variable] = set()
        for use_var in use_dict.values():
            all_vars.update(use_var)
        for def_var in def_dict.values():
            all_vars.update(def_var)

        lattice = LiveVarsLattice(all_vars)
        transfer = LiveVarsTransfer(use_dict, def_dict)
        analysis = DataFlowAnalysisFramework(
            cfg=self.cfg,
            lattice=lattice,
            transfer=transfer,
            direction='backward',
            init_value=set(),
            safe_value=set(),
            on_state_change=live_vars_on_state_change
        )

        analysis.analyze(strategy='worklist')