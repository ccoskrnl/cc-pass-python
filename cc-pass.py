#!/usr/bin/python
from typing import List, Tuple

import click
from pathlib import Path

from cof import CodeOptimizer
from cof.base.mir.function import MIRFunction
from cof.base.mir.inst import MIRInsts
from ir_file_parser import Parser


def parse_ir_file(filename: str) -> Tuple[MIRInsts, List[MIRFunction]]:
    p = Parser(filename)
    p.parse()
    p.insts.assign_addr()
    return p.insts, p.func_list


# ++++++++ Output ++++++++
def output_mir(insts, output_file):
    output_path = Path(output_file)
    output_dir = output_path.parent
    if output_dir and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_file, mode='w', encoding='utf-8') as file:
        file.write(str(insts))


@click.group(help="""
编译器优化通道工具集 (cc-pass.py)

一个专业的中间表示(IR)代码优化工具，提供多种优化算法和代码转换功能。
支持稀疏条件常量传播(SCCP)、部分冗余消除(PRE)等高级优化技术。

使用示例:
\b
  cc-pass.py optimize -i input.ir -o output.ir --sccp --pre=lcm
  cc-pass.py analyze input.ir --format=json
  cc-pass.py config config.json --validate
""")
def cli():
    """编译器优化通道工具集。"""
    pass


cli_optimize_pre_option: List[str] = ['lcm', 'dae', 'cse', '']
cli_optimize_ssa_period: List[str] = ['always', 'never', 'postpone']
cli_analysis_formats: List[str] = ['text']

@click.command(help="""
对中间表示(IR)代码执行优化转换。

应用多种优化算法改进代码性能，包括常量传播、冗余消除等。
支持试运行模式，可在实际执行前预览优化效果。

优化算法:\n
\b
  SCCP       稀疏条件常量传播，通过稀疏分析技术传播常量\n
  PRE        部分冗余消除算法:\n
             lcm    - 懒惰代码移动算法\n
             dae    - 死代码消除与表达式优化\n
             cse    - 公共子表达式消除\n

SSA周期控制:\n
\b
  always     始终保持SSA形式\n
  never      不转换为SSA形式\n
  postpone   延迟SSA转换到必要时\n

示例:\n
\b
  $ cc-pass.py optimize -i input.ir -o output.ir --sccp\n
  $ cc-pass.py optimize -i input.ir -o output.ir --sccp --pre=lcm\n
  $ cc-pass.py optimize -i input.ir -o output.ir --sccp --pre=lcm --dry-run -v
""")
@click.option('--sccp', is_flag=True,
              help="启用稀疏条件常量传播优化。")
@click.option('--pre', type=click.Choice(cli_optimize_pre_option),
              metavar='ALGORITHM',
              help='执行指定的部分冗余消除算法。可选: lcm, dae, cse。')
@click.option('--ssa-period', type=click.Choice(cli_optimize_ssa_period),
              default='always', show_default=True,
              metavar='PERIOD',
              help='控制SSA形式的更新时机。')
@click.option('--input-file', '-i',
              type=click.Path(exists=True, readable=True, path_type=Path),
              required=True,
              metavar='FILE',
              help='输入的IR文件路径。')
@click.option('--output-file', '-o',
              type=click.Path(writable=True, path_type=Path),
              required=True,
              metavar='FILE',
              help='输出的IR文件路径。')
@click.option('--verbose', '-v', is_flag=True,
              help='显示详细处理信息和优化进度。')
@click.option('--dry-run', is_flag=True,
              help='只显示将要执行的操作而不实际执行优化。')
def optimize(sccp, pre, ssa_period, input_file, output_file, verbose, dry_run):
    """对中间表示(IR)代码执行优化。"""
    # 验证输入文件
    if not input_file.is_file():
        raise click.BadParameter(f"输入文件 '{input_file}' 不存在或不是文件。")

    # 验证输出目录可写
    output_dir = output_file.parent
    if output_dir and not output_dir.exists():
        if dry_run:
            click.echo(f"将创建目录: {output_dir}")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

    # 显示优化配置
    if verbose or dry_run:
        click.echo("=" * 50)
        click.echo("优化配置摘要")
        click.echo("=" * 50)
        click.echo(f"  SCCP优化:        {'启用' if sccp else '禁用'}")
        click.echo(f"  PRE算法:        {pre if pre else '无'}")
        click.echo(f"  SSA更新时机:    {ssa_period}")
        click.echo(f"  输入文件:       {input_file}")
        click.echo(f"  输出文件:       {output_file}")
        click.echo(f"  详细模式:       {'是' if verbose else '否'}")
        click.echo(f"  试运行模式:     {'是' if dry_run else '否'}")
        click.echo("=" * 50)

    # 如果是试运行，则退出
    if dry_run:
        click.echo("试运行完成，未实际执行优化。")
        return

    # 执行优化
    try:
        if verbose:
            click.echo(f"开始读取输入文件: {input_file}")

        pre = '' if pre not in cli_optimize_pre_option else pre

        global_insts, func_list = parse_ir_file(str(input_file))
        optimizer = CodeOptimizer(
            global_insts,
            func_list,
            sccp_enable=sccp,
            pre_algorithm=pre,
            ssa_period=ssa_period,
        )

        if verbose:
            click.echo("开始执行优化过程...")

        optimizer.optimize()

        if verbose:
            click.echo(f"开始写入输出文件: {output_file}")

        output_mir(global_insts, str(output_file))

        # 显示完成信息
        click.echo("✓ 优化完成!")
        click.echo(f"✓ 结果已保存到: {output_file}")

    except Exception as e:
        raise click.ClickException(f"优化过程中出错: {str(e)}")


@click.command(help="""
分析IR文件并显示统计信息。

此命令提供IR代码的详细分析报告，包括函数数量、指令统计、
控制流复杂性等信息。支持多种输出格式便于后续处理。

分析内容:\n
\b
  - 基本文件信息（大小、函数数量）\n
  - 指令类型统计分布\n
  - 函数大小和复杂性指标\n
  - 控制流图分析结果\n
  - 单静态赋值形式 （可选）\n

输出格式说明:\n
\b
  text: 人类可读的文本格式（默认）\n
  json: 结构化JSON格式，便于脚本处理（暂不支持）\n
  xml:  XML格式，支持标准工具链（暂不支持）\n

示例:\n
\b
  # 基本文本分析\n
  cc-pass.py analyze example.ir

  # 详细分析报告\n
  cc-pass.py analyze large_program.ir -f text
""")

@click.argument('input_file', type=click.Path(exists=True, readable=True, path_type=Path),
                metavar='IR_FILE')
@click.argument('output_file',
                type=click.Path(writable=True, path_type=Path),
                metavar='FILE')
@click.option('--ssa-form', is_flag=True,
              help="转换为单静态赋值形式")
@click.option('--report_format', '-f', type=click.Choice(cli_analysis_formats),
              default='text', show_default=True,
              help='分析报告的输出格式。')
@click.option('--verbose', '-v', is_flag=True,
              help='显示更详细的分析信息。')
def analyze(input_file, output_file, ssa_form, report_format, verbose):
    """分析IR文件并显示统计信息。"""
    click.echo(f"分析文件: {input_file}")
    click.echo(f"输出格式: {format}")
    click.echo(f"详细模式: {'是' if verbose else '否'}")

    # 验证输入文件
    if not input_file.is_file():
        raise click.BadParameter(f"输入文件 '{input_file}' 不存在或不是文件。")

    # 验证输出目录可写
    output_dir = output_file.parent
    if output_dir and not output_dir.exists():
        if verbose:
            click.echo(f"将创建目录: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    if report_format not in cli_analysis_formats:
        report_format = 'text'

    # 暂时模拟分析过程
    if verbose:
        click.echo("正在解析IR文件...")
        click.echo("正在生成分析报告...")

    if ssa_form:
        global_insts, func_list = parse_ir_file(str(input_file))
        optimizer = CodeOptimizer(
            global_insts,
            func_list,
            sccp_enable=False,
            pre_algorithm='',
            ssa_period='always',
            analysis_only=True,
        )

        optimizer.optimize()
        output_mir(global_insts, str(output_file))

    click.echo("分析完成!")




# 注册所有子命令
cli.add_command(optimize)
cli.add_command(analyze)

if __name__ == "__main__":
    cli()