from typing import List, Dict, Tuple

from tabulate import tabulate

from cof.analysis.dataflow.framework import TransferCluster, B
from cof.base.bb import BasicBlock
from cof.base.mir.inst import MIRInstAddr
from cof.base.mir.variable import Variable
from cof.base.semilattice import Semilattice, T

type DefPoint = MIRInstAddr

def reaching_defs_on_state_change(block: BasicBlock, lattice, before: Tuple, after: Tuple):

    headers = [f"Block {block.id} "]
    row = ["Before"]
    row2 = ["After"]

    for idx, lat in enumerate(lattice.lattices):
        headers.append(str(lat.var))
        row.append(f"{{ {", ".join(map(str, before[idx]))} }}")
        row2.append(f"{{ {", ".join(map(str, after[idx]))} }}")

    table_data = [row, row2]
    print(tabulate(table_data, headers=headers, tablefmt="grid"), end="\n\n")



class ReachingDefsPowerSetSemilattice(Semilattice[set[DefPoint]]):

    def __init__(self, var: Variable, universal_set: set[DefPoint]):
        self.var = var
        self.universal_set = universal_set

    def top(self) -> T:
        return set()

    def bottom(self) -> T:
        return self.universal_set.copy()

    def partial_order(self, a: T, b: T) -> bool:
        return b.issubset(a)

    def meet(self, a: set[DefPoint], b: set[DefPoint]) -> set[DefPoint]:
        return a | b


class ReachingDefsProductSemilattice(Semilattice['Semilattice']):
    """
    Product Semilattice for Reaching Definitions Analysis.

    In data-flow analysis, a Product Semi-lattice is a Cartesian product of individual
    semilattices. Here, each unique variable in the program is assigned its own
    PowerSet Semilattice representing the set of points where that variable might
    have been defined.

    The state of the analysis is represented as a tuple, where each element corresponds to
    the lattice state of a specific value.
    """

    def __init__(self, defs_block: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]]):
        """
        Initialize the Product Semilattice by mapping each variable to its component lattice.

        Args:
            defs_block: A mapping from BasicBlocks to a list of definition pairs (Variable, DefPoint).
                        Used to discover all variables and their possible definition points
                        to construct the universal set for each power set lattice.
        """

        # var_to_lattice: Quick lookup to find the component lattice for a specific variable
        self.var_to_lattice: Dict[Variable, ReachingDefsPowerSetSemilattice] = { }

        # lattices: An ordered list of component lattices. The order here determines
        # the structure of the data-flow tuples (a_1, a_2, ..., a_n).
        self.lattices: List[ReachingDefsPowerSetSemilattice] = []

        # tuple_index: Maps a Variable to its integer index position within the product tuple.
        self.tuple_index: Dict[Variable, int] = { }


        self._initialize_lattices(defs_block)

    def _initialize_lattices(self, defs_block: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]]):
        """
        Scans the definitions to build a unique PowerSet Semilattice for every variable.
        Each variable's lattice will track its own 'Universal Set' of all possible
        Definition Points (DefPoints) for that variable.
        """
        for defs_list in defs_block.values():
            """
            As long as the dictionary content remains unmodified, the
            order returned by multiple calls to .values() will always
            be consistent with the insertion order.
            """
            for defs in defs_list:
                var: Variable = defs[0]
                def_point: DefPoint = defs[1]

                # Check if we have already encountered this variable
                lattice = self.var_to_lattice.get(var)

                # If it's a new variable, instantiate a new PowerSet Semilattice for it
                if not lattice:
                    # The set() here is the initial universal set, which grows as we scan
                    lattice = ReachingDefsPowerSetSemilattice(var, set())
                    self.lattices.append(lattice)

                    # Record the index position for this variable's component in the product
                    self.tuple_index[var] = len(self.lattices) - 1
                    self.var_to_lattice[var] = lattice

                # Add the current definition point to the variable's universal set
                # This defines the "boundary" of the power set for this specific variable
                lattice.universal_set.add(def_point)

    def meet(self, a: T, b: T) -> T:
        """
        Performs the 'meet' (confluence) operation component-wise across the product.
        For Reaching Definitions (usually a Union-based analysis), this typically
        combines the sets of reaching definitions for each variable.

        Returns:
            A tuple where the i-th element is the meet of a[i] and b[i].
        """
        return tuple(
            lat.meet(a_i, b_i)
            for lat, a_i, b_i in zip(self.lattices, a, b)
        )

    def top(self) -> T:
        """
        Returns the 'Top' element of the product lattice.
        In a product lattice L = L1 x L2 x ..., Top is the tuple (Top1, Top2, ...).
        For Reaching Definitions, this is usually an empty set for every variable.
        """
        return tuple(lat.top() for lat in self.lattices)

    def bottom(self) -> T:
        """
        Returns the 'Bottom' element of the product lattice.
        Usually represents the most conservative/least precise state (e.g., all
        definitions reach).
        """
        return tuple(lat.bottom() for lat in self.lattices)

    def partial_order(self, a: T, b: T) -> bool:
        """
        Determines if tuple 'a' is less than or equal to 'b' in the product partial order.
        In a product lattice, a <= b if and only if every component a_i <= b_i.

        Returns:
            True if a[i] <= b[i] for all i, False otherwise.
        """
        return all(
            lat.partial_order(a_i, b_i)
            for lat, a_i, b_i in zip(self.lattices, a, b)
        )


class ReachingDefsTransfer(TransferCluster):
    """
    Transfer Function for Reaching Definitions Analysis.

    This class defines how the set of reaching definitions changes as data
    flows through a Basic Block. It pre-calculates 'Gen' and 'Kill' sets
    to optimize the 'apply' operation during fixed-point iteration.
    """

    def __init__(self,
                 lattice: ReachingDefsProductSemilattice,
                 block_defs: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]]):
        """
        Initializes the transfer cluster by pre-computing the Gen and Kill
        information for every basic block in the control-flow graph.

        Args:
            lattice: The Product Semilattice defining the state space.
            block_defs: A dictionary mapping blocks to their contained definitions.
        """
        self.lattice = lattice
        self.block_defs = block_defs

        # block_kill_gen: Caches (Killed Variables, Gen Sets) for each block.
        # This prevents re-scanning blocks during the iterative analysis.
        self.block_kill_gen = {}

        for block, defs in block_defs.items():
            # 'Killed' variables: Any variable defined in this block will
            # "kill" any definitions of that same variable reaching from upstream.
            killed_vars = {var for var, _ in defs}

            # 'Gen' set: The set of definitions generated within this block
            # that are "locally visible" at the end of the block.
            # Note: For multiple definitions of the same variable in one block,
            # this logic assumes all definitions in the block 'reach' the exit.
            gen_sets = {}
            for var, def_stmt in defs:
                gen_sets.setdefault(var, set()).add(def_stmt)

            self.block_kill_gen[block] = (killed_vars, gen_sets)

    def apply(self, block: B, input_val: T) -> T:
        """
        Applies the transfer function to the input lattice state for a specific block.

        The operation follows the standard data-flow equation:
        Out = Gen \cup (In - Kill)

        In this implementation, because we use a Product Semilattice (one component
        per variable), the "Kill" is performed by overwriting the specific variable's
        component with the new "Gen" set from this block.

        Args:
            block: The current BasicBlock being analyzed.
            input_val: A tuple representing the IN state (Reaching Defs at block entry).

        Returns:
            A tuple representing the OUT state (Reaching Defs at block exit).
        """
        # Retrieve pre-computed Gen/Kill data; default to empty if block has no defs
        killed_vars, gen_sets = self.block_kill_gen.get(block, (set(), {}))

        # Convert tuple to list because lattice states are immutable;
        # we need to modify specific indices.
        out_state = list(input_val)

        # For every variable defined in this block:
        for var in killed_vars:
            # 1. Identify the position of this variable in the product tuple.
            idx = self.lattice.tuple_index[var]

            # 2. Update the state: This effectively 'kills' the incoming definitions
            # and 'generates' the new ones defined in the current block.
            out_state[idx] = gen_sets.get(var, set())

        # Return the new state as a tuple to maintain consistency with the Semilattice.
        return tuple(out_state)
