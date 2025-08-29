from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Generic, TypeVar, Dict, Optional, Callable, Iterable

T = TypeVar("T")
B = TypeVar("B")

class TransferCluster(ABC, Generic[B, T]):
    """Transfer Function"""

    @abstractmethod
    def apply(self, block: B, input_val: T) -> T:
        """applying transfer function: OUT[B] = f_B (IN(B))"""
        pass


class DataFlowAnalysisFramework(Generic[B, T]):
    """Generic data flow analysis framework supporting forward and backward analyses.

    Attributes:
        cfg: Control flow graph of the program
        lattice: Abstract semilattice defining the value domain and operations
        transfer: Transfer function implementation for basic blocks
        direction: Analysis direction ('forward' or 'backward')
        merge: Function for merging values at control flow joins
        on_state_change: Optional callback for state change events
    """
    def __init__(self,
                 cfg: 'ControlFlowGraphForDataFlowAnalysis',
                 lattice: 'Semilattice[T]',
                 transfer: 'TransferCluster[B, T]',
                 direction: str = 'forward',  # 'forward' or 'backward'
                 init_value: T = None,
                 safe_value: T = None,
                 merge_operation: Optional[Callable[[Iterable[T]], T]] = None,
                 on_state_change: Optional[Callable[[B, 'Semilattice[T]', T, T], None]] = None):
        """
        Initialize the data flow analysis framework.

        Args:
            cfg: Control flow graph
            lattice: Semilattice defining the value domain
            transfer: Transfer function implementation
            direction: Analysis direction ('forward' or 'backward')
            init_value: Initial value for the entry/exit block
            safe_value: Safe value for other blocks
            merge_operation: Function for merging values (default: lattice.meet)
            on_state_change: Callback for state change events
        """
        assert init_value is not None, "Initial value must be provided"
        assert safe_value is not None, "Safe value must be provided"

        self.cfg = cfg
        self.lattice = lattice
        self.transfer = transfer
        self.direction = direction
        self.on_state_change = on_state_change

        # Adjust CFG according to analysis direction
        self.working_cfg = cfg if direction == 'forward' else cfg.reverse()

        # Use lattice.meet if no custom merge operation is provided
        self.merge = merge_operation if merge_operation else lattice.meet

        # Initialize analysis states
        self.in_states: Dict[B, T] = { }
        self.out_states: Dict[B, T] = { }

        self.result: Dict[B, T] = { }

        self._initialize_states(init_value, safe_value)

    def _initialize_states(self, init_value: T, safe_value: T):
        """Initialize analysis states for all blocks.

        Args:
            init_value: Value for the entry/exit block
            safe_value: Value for other blocks
        """
        # Initialize all blocks with safe value
        for block in self.working_cfg.all_blocks():
            self.in_states[block] = deepcopy(safe_value)
            self.out_states[block] = deepcopy(safe_value)

        # Set initial value for the starting block
        entry_block = self.working_cfg.entry_block()
        if self.direction == 'forward':
            self.out_states[entry_block] = deepcopy(init_value)
        else:
            self.in_states[entry_block] = deepcopy(init_value)

    def analyze(self, strategy='worklist') -> Dict[B, T]:
        """
        perform data-flow analysis
        :param strategy: iteration strategy (worklist or round-robin)
        :return: OUT if direction is forward, otherwise IN.
        """

        if strategy == 'worklist':
            return self._analyze_worklist()
        else:
            return { }

    def _analyze_worklist(self) -> Dict[B, T]:
        """Perform worklist algorithm for data flow analysis.

        Returns:
            Dictionary of final states for all blocks
        """

        # Initialize worklist with all blocks except the entry block.
        worklist = set(self.working_cfg.all_blocks())
        entry_block = self.working_cfg.entry_block()
        worklist.discard(entry_block)

        # Track iterations to prevent infinite loops
        max_iterations = len(worklist) * 10         # Heuristic for convergence limit
        iteration_count = 0

        neighbor_getter = self.working_cfg.predecessors
        affected_block_getter = self.working_cfg.successors

        # Configure analysis direction
        if self.direction == 'forward':
            # Forward analysis: propagate from predecessors to successors
            input_states: Dict[B, T] = self.in_states
            output_states: Dict[B, T] = self.out_states
        else:
            # Backward analysis: propagate from successors to predecessors
            output_states: Dict[B, T] = self.in_states
            input_states: Dict[B, T] = self.out_states
            # neighbor_getter = self.working_cfg.successors
            # affected_block_getter = self.working_cfg.predecessors

        # Process worklist until convergence or iteration limit
        while worklist and iteration_count < max_iterations:

            iteration_count += 1
            block = worklist.pop()

            # Get neighbors based on analysis direction
            neighbors = neighbor_getter(block.id)

            # Only process if there are neighbors (avoid empty list)
            if neighbors:
                # Collect neighbor output values
                neighbor_values = [output_states[b] for b in neighbors]
                # Compute new input value by merging neighbor outputs
                new_input_value = neighbor_values[0]
                for neighbor in neighbor_values[1:]:
                    new_input_value = self.lattice.meet(new_input_value, neighbor)

                # Update input state if changed
                if new_input_value != input_states[block]:
                    input_states[block] = new_input_value
            else:
                # No neighbors, keep existing input state
                new_input_value = input_states[block]

            # Apply transfer function to get new output value
            new_output_value = self.transfer.apply(block, new_input_value)

            # Check if output state changed
            if new_output_value != output_states[block]:
                # Notify state change callback if provided
                if self.on_state_change:
                    self.on_state_change(block, self.lattice, output_states[block], new_output_value)

                # Update output state
                output_states[block] = new_output_value

                # Add affected neighbors to worklist
                # For forward analysis: successors; backward: predecessors
                affected_blocks = affected_block_getter(block.id)
                worklist.update(affected_blocks)

        # Warn if analysis didn't converge
        if iteration_count >= max_iterations:
            print(f"Warning: Analysis did not converge in {max_iterations} iterations")

        self.result = output_states
        return self.result
