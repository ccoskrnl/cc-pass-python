# Code Optimization Framework

***

## 介绍

Python实现的程序分析框架，可作为编译器后端。正在开发中。

***
## 演示

C 语言伪代码

```c
k = false;
i = 1;
j = 2;
while ( i <= n)
{
	j = j * 2;
	k = true;
	if (i <= 5)
	{
	    i = i + 1;
   }
}
if (k)
{
	printf(j);
}
else
{
	i += 1;
}
```

自定义MIR格式

``` 
    entry
    k := false
    i := 1
    j := 2
L1:
    cond1 := i <= n
    if cond1 goto &L2
    if k goto &L4
    i := i + 1
    goto &L5
L2:
    j := j * 2
    k := true
    cond2 := i <= 5
    if cond2 goto &L3
    goto &L1
L3:
    i := i + 1
    goto &L1
L4:
    print j
    goto &L5
L5:
    exit
```

可视化控制流图展示

![cfg_demo](./tmp/readme_ref_img01.png)

***

## TODO

- [ ] 数据流分析框架
- [ ] 最小化SSA计算
- [ ] 稀有条件常量传播(符号执行)
- [ ] 高级数据流分析
- [ ] 控制树规约

## License

无