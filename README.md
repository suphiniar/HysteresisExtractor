```
# HysteresisExtractor
拟静力试验滞回曲线关键信息提取与本构参数识别工具

## 项目简介
本工具面向土木工程构件拟静力循环加载试验，针对原始滞回试验数据完成全套后处理流程：自动识别开裂点、峰值点、极限点并生成骨架曲线；基于提取得到的特征点，使用智能优化算法对 OpenSees `Hysteretic` 材料本构参数进行反演识别，输出可直接用于有限元计算的本构参数文件。

## 技术栈
- Python 3.x
- 数值计算：`numpy`、`scipy`
- 绘图可视化：`matplotlib`
- 智能优化算法：`mealpy`
- 有限元仿真：`openseespy`
- 评价指标：`scikit‑learn`
- 数据存储：json、txt 文本格式

## 文件说明
### 核心脚本
1. **Feature point.py**
滞回曲线特征点提取主程序。读取`Hysteretic`文件夹下试验txt数据，自动分割各个滞回环，生成骨架曲线；通过斜率突变、面积等效算法识别开裂点、峰值点、极限点。输出骨架曲线文本文件、特征点文本文件，同时输出标记特征点的滞回‑骨架曲线图片。
> 输出图片存放至`Figure`目录，特征点数据保存到`F`文件夹。

2. **Optimization.py**
本构参数反演识别模块。
读取特征点数据，搭建 OpenSeesPy 单自由度 SDOF 计算模型；
支持两种优化算法：`ARO`算法、`模拟退火+Nelder‑Mead单纯形(SA+NM‑simplex)`；
以仿真滞回曲线与试验滞回曲线的均方误差作为目标函数，优化识别 Hysteretic 材料的 `pinchX、pinchY、damage1、damage2、beta` 参数；
输出优化结果json文件、试验与仿真对比图、仿真单独滞回曲线。

3. **合并本构参数.py**
读取特征点文件以及优化输出的json结果，合并输出`parameters.txt`，整合完整的Hysteretic本构输入参数，供后续有限元程序调用。

### 目录结构
```

HysteresisExtractor/
├── Feature point.py                # 特征点提取、骨架曲线生成主程序
├── Optimization.py                 # 本构参数优化识别模块
├── 合并本构参数.py                  # 特征点与优化参数合并输出
├── README.md                       # 项目说明文档
├── requirements.txt                # Python 依赖清单
├── .gitignore                      # Git 忽略配置
├── parameters.txt                  # 输出：合并后的完整本构参数
├── path.txt                        # 位移加载路径配置文件
├── Hysteretic/                     # 输入：原始滞回试验数据 txt
├── HystereticCurves/               # 输入：用于参数识别的试验数据
├── backbone/                       # 输出：骨架曲线 txt 文件（git 忽略）
├── F/                              # 输出：开裂 / 峰值 / 极限特征点 txt（git 忽略）
├── Figure/                         # 输出：标记特征点的滞回 & 骨架曲线图（git 忽略）
├── FigureOptim/                    # 输出：试验 vs 仿真滞回对比图（git 忽略）
├── FigureOptimSingle/              # 输出：优化后仿真滞回曲线及数据（git 忽略）
└── OptimizationResults/            # 输出：优化结果 json 文件（git 忽略）

```

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用流程

> 
> ⚠️执行顺序：**先提取特征点 → 再执行参数优化 → 最后合并本构参数**

1. **准备输入数据**
将原始滞回试验文本数据放入 `Hysteretic` 文件夹；
用于参数识别的试验数据放入 `HystereticCurves`；
根据实际工况修改配置文件 `path.txt`，填写位移加载路径。
2. **步骤 1：提取特征点与骨架曲线**
运行 `Feature point.py`
程序批量处理文件夹内 txt 格式试验数据：

- `backbone/`：输出骨架曲线数据
- `F/`：输出开裂点、峰值点、极限点特征数据
- `Figure/`：输出标记特征点的可视化图片

3. **步骤 2：Hysteretic 本构参数优化识别**
运行 `Optimization.py`
可在脚本内部修改优化配置：`pop_size`种群规模、`epoch`迭代次数，选择优化算法 `ARO` 或者 `SA + NM‑simplex`。
输出内容：

- `OptimizationResults/`：json 格式优化结果，包含 pinch、damage、beta 参数、拟合误差、计算耗时
- `FigureOptim/`：试验‑仿真滞回对比图
- `FigureOptimSingle/`：仿真输出滞回曲线与对应文本数据

4. **步骤 3：合并特征点与优化参数**
运行 `合并本构参数.py`
自动读取`F`文件夹特征点与`OptimizationResults`下的优化 json，合并生成`parameters.txt`，得到完整 Hysteretic 材料输入参数。

## 算法说明

1. **骨架曲线生成**：分割各个循环滞回环，提取每个滞回环正负向极值点，过滤同一荷载等级重复点，得到骨架曲线；
2. **特征点识别**：利用斜率突变识别拐点，面积等效法求解开裂点；骨架曲线上的极值作为峰值点；面积等效方法求解极限点；
3. **参数反演**：建立 SDOF 单自由度 OpenSeesPy 模型，以仿真滞回与试验滞回 RMSE 误差最小作为目标，采用元启发式优化算法反演 Hysteretic 本构 5 个关键参数。

## 注意事项

1. 输入 txt 文件格式：两列数据，第一列为位移 (mm)，第二列为荷载 (kN)；
2. OpenSees 内部力单位为 N，程序内部已经完成 kN‑N 的单位换算，无需手动修改；
3. 优化计算耗时受种群规模、迭代轮数影响，可根据电脑性能调整`pop_size`、`epoch`；
4. 当前版本仅支持 `Hysteretic` 本构模型。

## 声明

本程序仅用于科研试验数据后处理。使用者自行对数据处理、参数反演结果以及后续有限元分析结果负责。
