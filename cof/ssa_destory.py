from cof.analysis.dataflow import DataFlowAnalyzer
from cof.base.cfg import ControlFlowGraphForDataFlowAnalysis


def compute_live_range(cfg: ControlFlowGraphForDataFlowAnalysis,):
    data_flow_analyzer = DataFlowAnalyzer(cfg=cfg)
    liveness_analysis_result = data_flow_analyzer.live_vars()
    live_ranges = { }
    for block in cfg.all_blocks():
        for var in liveness_analysis_result[block]:
            if var not in live_ranges:
                live_ranges[var] = set()
            live_ranges[var].add(block)
