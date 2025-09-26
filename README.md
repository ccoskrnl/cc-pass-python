# cc-pass-python

**这并不是一个可用的工具，只是出于学习的目的**


## 目录

- [介绍](#介绍)
- [特性](#特性)
- [使用](#使用)
- [路标](#路标)
- [联系](#联系)

## 介绍

由Python实现的程序分析框架，通过对传入的MIR进行解析转化成控制流图，对控制流图进行静态分析为后续的优化或者反编译做指导。已经支持数据流分析框架，并包含一些经典的数据流分析问题，如到达定值，活跃变量分析等。同时支持使用符号执行的稀疏条件的常量传播。后续会逐渐添加更强大更复杂的分析算法。

类似 `llvm-pass` 那样，`cc-pass` 也将会支持输入原始的 `ir` 并给出优化后的 `ir`。现阶段实现的分析器不够强大，待分析器完善后，并添加一些优化算法之后将会开始支持此功能。

在可视化方面，框架内置了一个根据PyQt6开发的控制流图可视化器。在布局方面，可视化器使用 [Reingold-Tilford算法](https://github.com/ccoskrnl/tree_layout_demo) 对控制流图进行初始的布局，但每个基本块都被设置为可拖动的节点。在控制流图边绘制这方面并没有进行很好的实现，对于特殊边的处理效果更是混乱。



## 特性

### MIR

框架使用自定义的MIR

```
# test/example.ir

    %entry
	%init n

    k := false
    i := 1
    j := 2
L1:
    cond1 := i <= n
    %if cond1 %goto &L2
    %if k %goto &L4
    i := i + 1
    %goto &L5
L2:
    j := j * 2
    k := %true
    cond2 := i <= 5
    %if cond2 %goto &L3
    i := i - 1
    %goto &L1
L3:
    i := i + 1
    %goto &L1
L4:
    printf ( i j k )
    %goto &L5

L5:
    %exit
```

| **元素类型**              | **示例代码**               | **功能说明**                                                 |
| ------------------------- | -------------------------- | ------------------------------------------------------------ |
| **基本块（Basic Block）** | `%entry`、`L1:`、`L2:`     | 以标签定义代码块，包含顺序语句和终结指令；`%entry` 为入口块。 |
| **变量赋值**              | `k := false`、`i := 1`     | 用 `:=` 初始化或更新变量，支持布尔值、整数等基本类型。       |
| **条件跳转**              | `%if cond1 %goto &L2`      | 若条件成立（如 `cond1` 为真），跳转到目标块（`L2`）。        |
| **无条件跳转**            | `%goto &L1`                | 强制跳转到指定块，用于循环或分支合并。                       |
| **算术运算**              | `j := j * 2`、`i := i + 1` | 支持加减乘除等运算，直接操作变量。                           |
| **函数调用**              | `printf(i j k)`            | 嵌入外部函数，参数以空格分隔。                               |
| **程序边界标记**          | `%exit`                    | 标识程序终止点，辅助编译器优化资源释放。                     |

### 控制流图可视化

上面的MIR在被转换为控制流图后可以被控制流图可视化器绘制。效果如下图所示：

![cfg_demo](./tmp/readme_ref_img01.png)

### 数据流框架

在数据流分析算法的实现中，框架并没有遵循严格意义上的“交半格”或者“并半格“，而是统一使用”并半格“的概念。这样的好处是只要我们选择合适的meet操作以及初始值和安全值就可以统一的对各种常规的数据流问题进行求解。框架的参数如下：

```python
class DataFlowAnalysisFramework(Generic[T, B]):
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
                 transfer: 'TransferFunction[T, B]',
                 direction: str = 'forward', # 'forward' or 'backward'
                 init_value: T = None,
                 safe_value: T = None,
                 merge_operation: Optional[Callable[[Iterable[T]], T]] = None,
                 on_state_change: Optional[Callable[[B, T, T], None]] = None):
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
```

### 稀疏条件的常量传播

稀疏条件的常量传播（Sparse Conditional Constant Propagation，SCCP）是普通常量传播的增强版，结合了**常量传播**与**条件分支分析**，能更精确地处理控制流和稀疏数据流。框架首先通过迭代必经边界方法将流图转换为最小的SSA形式，并对基本块进行扁平化（或原子化），并使用流图的边和SSA边来传递信息实现程序的符号执行。


## 使用
```commandline
$ python cc-pass.py --help                                                                                                               
Usage: cc-pass.py [OPTIONS] COMMAND [ARGS]...

  编译器优化通道工具集 (cc-pass.py)

  一个专业的中间表示(IR)代码优化工具，提供多种优化算法和代码转换功能。 支持稀疏条件常量传播(SCCP)、部分冗余消除(PRE)等高级优化技术。

  使用示例:   cc-pass.py optimize -i input.ir -o output.ir --sccp --pre=lcm
  cc-pass.py analyze input.ir --format=json   cc-pass.py config config.json
  --validate

Options:
  --help  Show this message and exit.

Commands:
  analyze   分析IR文件并显示统计信息。
  optimize  对中间表示(IR)代码执行优化转换。
```

```commandline
$ python cc-pass.py optimize --help                                                                                                      
Usage: cc-pass.py optimize [OPTIONS]

  对中间表示(IR)代码执行优化转换。

  应用多种优化算法改进代码性能，包括常量传播、冗余消除等。 支持试运行模式，可在实际执行前预览优化效果。

  优化算法:

    SCCP       稀疏条件常量传播，通过稀疏分析技术传播常量

    PRE        部分冗余消除算法:

               lcm    - 懒惰代码移动算法

               dae    - 死代码消除与表达式优化

               cse    - 公共子表达式消除

  SSA周期控制:

    always     始终保持SSA形式

    never      不转换为SSA形式

    postpone   延迟SSA转换到必要时

  示例:

    $ cc-pass.py optimize -i input.ir -o output.ir --sccp

    $ cc-pass.py optimize -i input.ir -o output.ir --sccp --pre=lcm

    $ cc-pass.py optimize -i input.ir -o output.ir --sccp --pre=lcm --dry-run
    -v

Options:
  --sccp                  启用稀疏条件常量传播优化。
  --pre ALGORITHM         执行指定的部分冗余消除算法。可选: lcm, dae, cse。
  --ssa-period PERIOD     控制SSA形式的更新时机。  [default: always]
  -i, --input-file FILE   输入的IR文件路径。  [required]
  -o, --output-file FILE  输出的IR文件路径。  [required]
  -v, --verbose           显示详细处理信息和优化进度。
  --dry-run               只显示将要执行的操作而不实际执行优化。
  --help                  Show this message and exit.
```

```commandline
$ python cc-pass.py analyze --help                                                                                                       
Usage: cc-pass.py analyze [OPTIONS] IR_FILE FILE

  分析IR文件并显示统计信息。

  此命令提供IR代码的详细分析报告，包括函数数量、指令统计、 控制流复杂性等信息。支持多种输出格式便于后续处理。

  分析内容:

    - 基本文件信息（大小、函数数量）

    - 指令类型统计分布

    - 函数大小和复杂性指标

    - 控制流图分析结果

    - 单静态赋值形式 （可选）

  输出格式说明:

    text: 人类可读的文本格式（默认）

    json: 结构化JSON格式，便于脚本处理（暂不支持）

    xml:  XML格式，支持标准工具链（暂不支持）

  示例:

    # 基本文本分析

    cc-pass.py analyze example.ir

    # 详细分析报告

    cc-pass.py analyze large_program.ir -f text

Options:
  --ssa-form                  转换为单静态赋值形式
  -f, --report_format [text]  分析报告的输出格式。  [default: text]
  -v, --verbose               显示更详细的分析信息。
  --help                      Show this message and exit.
```

## 路标

- [x] 数据流分析框架
- [x] 稀有条件常量传播(符号执行)
- [x] Lazy-Code Motion
- [ ] 循环依赖分析
- [ ] 别名分析
- [ ] 高级数据流分析
- [ ] 控制树规约



## 联系

E-mail: 2010705797@qq.com



## License

无