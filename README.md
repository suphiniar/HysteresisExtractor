# HysteresisExtractor
```
# HysteresisExtractor
拟静力试验滞回曲线关键信息提取与本构参数识别工具

## 项目简介
本工具针对构件拟静力循环加载试验，从原始滞回试验数据文本完成整套后处理：自动识别开裂点、峰值点、极限点，生成骨架曲线；基于特征点，采用优化算法对OpenSees `Hysteretic` 材料本构参数进行反演识别，输出可直接使用的本构参数文件。

## 技术栈
- Python 3.x
- 数值计算：`numpy`、`scipy`
- 绘图可视化：`matplotlib`
- 智能优化：`mealpy`
- 有限元仿真：`openseespy`
- 数据存储：json、txt文本

## 文件说明
### 核心脚本
1. **Feature point.py**
滞回曲线特征点提取主程序。读取`Hysteretic`文件夹下试验txt数据，分割各滞回环，生成骨架曲线；通过面积等效、斜率突变识别**开裂点、峰值点、极限点**；输出骨架曲线文本、特征点文本，同时输出绘制标记特征点的滞回‑骨架曲线图，图片输出至`Figure`目录，特征点保存到`F`文件夹。

2. **Optimization.txt（可重命名为Optimization.py）**
本构参数反演识别模块。
- 读取特征点文件，构建OpenSeesPy单自由度SDOF模型；
- 支持两种优化算法：`ARO`算法、`模拟退火+Nelder‑Mead单纯形(SA+NM‑simplex)`；
- 以仿真‑试验滞回曲线均方误差作为目标函数，优化Hysteretic材料`pinchX/pinchY/damage1/damage2/beta`参数；
- 输出优化结果json至`OptimizationResults`，输出仿真对比图到`FigureOptim`、`FigureOptimSingle`。

3. **合并本构参数.py**
读取特征点文件与优化得到的json结果，合并输出`parameters.txt`，整合全部本构输入参数，可直接用于后续有限元调用。

### 目录结构
```

HysteresisExtractor/
├── Feature point.py                # 特征点提取、骨架曲线生成
├── Optimization.py                 # 本构参数优化识别
├── 合并本构参数.py                  # 特征点 + 优化参数合并输出 parameters.txt
├── parameters.txt                  # 输出：合并后的完整本构参数
├── path.txt                        # 位移路径配置文件
├── Hysteretic/                     # 输入：原始滞回试验数据 txt
├── HystereticCurves/               # 输入：用于参数识别的试验数据
├── backbone/                       # 输出：骨架曲线 txt 文件
├── F/                              # 输出：开裂 / 峰值 / 极限特征点 txt
├── Figure/                         # 输出：标记特征点的滞回 & 骨架曲线图
├── FigureOptim/                    # 输出：试验 vs 仿真滞回对比图
├── FigureOptimSingle/              # 输出：优化后仿真滞回曲线及数据
├── OptimizationResults/            # 输出：优化结果 json 文件
├── .gitignore                      # Git 忽略配置
└── requirements.txt                # Python 依赖

```

## 安装依赖
```bash
pip install -r requirements.txt
```

requirements.txt 内容参考：

```
numpy
matplotlib
scipy
mealpy
openseespy
scikit‑learn
```

## 使用流程

> 
> ⚠️执行顺序：**先提取特征点 → 再做参数优化 → 最后合并参数**

1. **准备输入数据**
将原始滞回试验文本数据放入 `Hysteretic` 文件夹；
用于参数识别的数据放入 `HystereticCurves`；
配置`path.txt`位移加载路径。
2. **步骤 1：提取特征点与骨架曲线**
运行 `Feature point.py`
程序自动批量处理文件夹内 txt：

- `backbone/`：输出骨架曲线
- `F/`：输出开裂点、峰值点、极限点特征数据
- `Figure/`：输出绘制特征标记的图片

3. **步骤 2：Hysteretic 本构参数优化识别**
运行 `Optimization.py`

> 
> 可在脚本内修改配置：`pop_size`种群规模、`epoch`迭代次数、优化算法选择`ARO`或`SA + NM‑simplex`
> 输出内容：

- `OptimizationResults/`：保存各样本优化结果 json，包含 pinch、damage、beta 参数与拟合误差、计算耗时
- `FigureOptim/`：试验‑仿真滞回对比图
- `FigureOptimSingle/`：仿真输出滞回曲线与对应文本数据

4. **步骤 3：合并特征点与优化参数**
运行 `合并本构参数.py`
自动读取`F`特征点文件与`OptimizationResults`优化 json，合并生成`parameters.txt`，得到完整 Hysteretic 材料输入参数。

## 算法说明

1. 骨架曲线：分割各循环滞回环，提取每环极值，过滤同等级重复点，得到骨架曲线；
2. 特征点识别：斜率突变识别拐点，面积等效法求解开裂点；取骨架峰值作为峰值点；面积等效求解极限点；
3. 参数反演：建立 SDOF 单自由度 OpenSeesPy 模型，以仿真滞回与试验滞回的 RMSE 误差最小作为目标，采用元启发式优化算法反演 Hysteretic 本构 5 个关键参数。

## 注意事项

1. 输入 txt 格式：两列数据，第一列为位移 (mm)，第二列为荷载 (kN)；
2. OpenSees 内部单位为 N，程序内部已经做 kN‑N 单位换算；
3. 优化计算耗时取决于种群规模与迭代轮数，建议根据计算机性能调整`pop_size`、`epoch`；
4. 仅支持`Hysteretic`单种本构模型。

## 声明

> 
> 本程序仅用于科研试验数据后处理。使用者自行对数据处理、参数反演结果及后续有限元分析结果负责。
