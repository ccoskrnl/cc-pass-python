# Code Optimization Framework

***

## 介绍

Python实现的程序分析框架，可作为编译器后端。正在开发中。

***
## 演示

自定义MIR语法
```
# test/ssa_example.ir

    entry
    k := false
    i := 1
    j := 2
L1:
    cond1 := i <= n
    if cond1 goto &L2
    if k goto &L3
    i := i + 1
    goto &L4
L2:
    j := j * 2
    k := true
    i := i + 1
    goto &L1
L3:
    print j
L4:
    exit
```

可视化控制流图展示

![cfg_demo](./tmp/readme_ref_img01.png)

最小化SSA计算展示

![minimal_ssa](./tmp/readme_ref_mininal_ssa.png)

***

## TODO

- [ ] 数据流分析框架
- [x] 最小化SSA计算
- [ ] 稀有条件常量传播(符号执行)
- [ ] 高级数据流分析
- [ ] 控制树规约

## License

无