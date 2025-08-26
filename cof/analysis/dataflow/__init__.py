from typing import Dict, List, Tuple

from tabulate import tabulate

from cof.analysis.dataflow.anticipated_exprs import AnticipatedSemilattice, AnticipatedTransfer, \
    anticipated_exprs_on_state_change
from cof.analysis.dataflow.framework import DataFlowAnalysisFramework
from cof.analysis.dataflow.live_vars import LiveVarsLattice, LiveVarsTransfer, live_vars_on_state_change
from cof.analysis.dataflow.reaching_defs import DefPoint, ReachingDefsProductSemilattice, ReachingDefsTransfer, \
    reaching_defs_on_state_change
from cof.base.bb import BasicBlock
from cof.base.cfg import ControlFlowGraphForDataFlowAnalysis
from cof.base.expr import Expression
from cof.base.mir import Variable


class DataFlowAnalyzer:
    def __init__(self, cfg: ControlFlowGraphForDataFlowAnalysis):
        self.cfg = cfg

    def reaching_definitions(self):

        defs_block: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]] = self.cfg.collect_definitions()
        lattice = ReachingDefsProductSemilattice(defs_block)
        transfer = ReachingDefsTransfer(lattice, defs_block)

        analysis = DataFlowAnalysisFramework(
            cfg=self.cfg,
            lattice=lattice,
            transfer=transfer,
            direction='forward',
            init_value=lattice.top(),
            safe_value=lattice.top(),
            on_state_change=reaching_defs_on_state_change
        )

        analysis.analyze(strategy='worklist')
        print("\n\n++++++++++++++++++++++++++++++ Analysis Result ++++++++++++++++++++++++++++++")
        headers = [""]
        table_data = [ ]
        for lat in lattice.lattices:
            headers.append(str(lat.var))

        for b, t in analysis.result.items():
            row = [f"Block {b.id}"]
            for d in t:
                row.append(f"{{ {", ".join(map(str, d))} }}")
            table_data.append(row)

        print(tabulate(table_data, headers=headers, tablefmt="grid"), end="\n\n")




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
            init_value=lattice.top(),
            safe_value=lattice.bottom(),
            on_state_change=live_vars_on_state_change
        )

        analysis.analyze(strategy='worklist')
        print("\n\n++++++++++++++++++++++++++++++ Analysis Result ++++++++++++++++++++++++++++++")

        info = ""
        for b, t in analysis.result.items():
            info += f"Block {b.id}: {{ {", ".join(map(str, t))} }}\n"

        print(info)


    def anticipated_exprs(self) -> Dict[BasicBlock, set[Expression]]:
        all_exprs = self.cfg.collect_exprs()
        lattice = AnticipatedSemilattice(all_exprs)
        transfer = AnticipatedTransfer(all_exprs, self.cfg.all_blocks())
        analysis = DataFlowAnalysisFramework(
            cfg=self.cfg,
            lattice=lattice,
            transfer=transfer,
            direction='backward',
            init_value=lattice.bottom(),
            safe_value=lattice.top(),
            on_state_change=anticipated_exprs_on_state_change,
        )
        analysis.analyze(strategy='worklist')
        print("\n\n++++++++++++++++++++++++++++++ Analysis Result ++++++++++++++++++++++++++++++")
        info = ""
        for b, t in analysis.result.items():
            info += f"Block {b.id}: {{ {", ".join(map(str, t))} }}\n"

        print(info)

        return analysis.result
