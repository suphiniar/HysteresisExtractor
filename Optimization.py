import numpy as np
from sklearn.metrics import mean_squared_error
from mealpy import FloatVar, ARO
from scipy.optimize import minimize, dual_annealing
import openseespy.opensees as ops
from pathlib import Path
import json
import matplotlib.pyplot as plt
import time
import os

def optimize(disp, force, material, algorithm, config, points):
    '''
    滞回模型参数识别函数
    disp: 滞回曲线的位移
    force: 滞回曲线的力
    material: 滞回模型名称，目前只有'Hysteretic'一个选项
    algorithm: 优化算法名称，'ARO' or 'SA + NM-simplex'
    config: 优化算法设置，可参考config = {'pop_size': 50, 'epoch': 1000, 'early_stop': 10}
    points: 已知的屈服点、峰值点和极限点数据
    '''
    # 滞回曲线的正负向峰值点（力，位移）
    positive_peak = [np.max(force), disp[np.argmax(force)]]
    negative_peak = [np.min(force), disp[np.argmin(force)]]
    # 滞回曲线的正负向最大位移点（力，位移）
    max_d_point = [force[np.argmax(disp)], np.max(disp)]
    min_d_point = [force[np.argmin(disp)], np.min(disp)]

    bounds, x0, mat_model, method, config = [], [], None, None, {}
    # 选择滞回模型，目前只有Hysteretic能用
    if material == 'Hysteretic':
        # 设置待优化参数的取值范围，待优化参数有：
        # pinchX pinchY
        # damage1 damage2
        # beta
        bounds = [[0.001, 1.], [0.001, 1.],
                  [0.001, 1.], [0.001, 1.],
                  [0.001, 1.]]

        # 设置初值（ARO算法用不上，SA + NM-simplex方法需要）
        x0 = [0.999, 0.999, 0.001, 0.001, 0.001]
        x0 = np.array(x0)

        mat_model = Hysteretic

    # 选择优化算法
    if algorithm == 'ARO':
        method = aro
    if algorithm == 'SA + NM-simplex':
        method = SA_NMsimplex

    def __objective(x):
        '''
        优化问题的目标函数
        x: 滞回模型参数值，是一个列表，包含所有待优化的参数
        '''
        # 用OpenSees对单自由度体系进行静力分析
        SDOF(mat_model, x, points, 1)
        disp_, force_ = static(disp)
        force_ = -force_
        # 计算单自由度体系的力和原始滞回曲线的力之间的百分比误差
        error = np.sqrt(mean_squared_error(force, force_)) / positive_peak[0] * 100
        return round(error, 0)

    # 依据初值、目标函数、参数取值范围等进行优化过程，得到最优参数向量 x 和百分比误差 error
    x, error = method(x0, __objective, bounds, config)

    # 添加返回值，包括优化参数向量 x、百分比误差 error、正负向峰值点及其位移
    return x, error


def aro(x0, object_func, bounds, config = None):
    '''
    ARO优化算法
    '''
    if config:
        pop_size, epoch, early_stop = config['pop_size'], config['epoch'], config['early_stop']
    else:
        pop_size, epoch, early_stop = 50, 1000, 30

    LB, UB = [], []
    for bound in bounds:
        LB.append(bound[0])
        UB.append(bound[1])
    LB, UB = np.array(LB), np.array(UB)

    problem_dict = {
        'bounds': FloatVar(lb=LB, ub=UB),
        'obj_func': object_func,
        'minmax': 'min',
    }

    term_dict = {
        "max_early_stop": early_stop
    }

    model = ARO.IARO(epoch, pop_size)
    g_best = model.solve(problem_dict, termination=term_dict, seed=2024)
    return g_best.solution, g_best.target.fitness


def SA_NMsimplex(x0, object_func, bounds, config = None):
    '''
    另一种优化算法
    '''
    DA = dual_annealing(object_func, bounds=bounds, no_local_search=True, x0=x0)
    NMsimplex = minimize(object_func, x0=DA['x'], bounds=bounds, method='Nelder-Mead')
    return NMsimplex['x'], NMsimplex['fun']


def Hysteretic(matID, params, points):
    '''
    Hysteretic本构材料
    注意下面材料中力乘1000是因为力的基本单位是N，但是读取的特征点的力的单位是kN
    '''
    ops.uniaxialMaterial('Hysteretic', matID,
                         points[0][1] * 1000, points[0][0],  # yield positive (force, disp)
                         points[1][1] * 1000, points[1][0],  # peak positive (force, disp)
                         points[2][1] * 1000, points[2][0],  # ultimate positive (force, disp)
                         points[3][1] * 1000, points[3][0],  # yield negative (force, disp)
                         points[4][1] * 1000, points[4][0],  # peak negative (force, disp)
                         points[5][1] * 1000, points[5][0],  # ultimate negative (force, disp)
                         params[0], params[1],        # pinchX, pinchY
                         params[2], params[3],        # damage1, damage2
                         params[4])                   # beta


def SDOF(material, params_mat, points, mass):
    '''
    用OpenSeesPy建立一维单自由度体系的函数
    '''
    ops.wipe()
    ops.model('BasicBuilder', '-ndm', 1, '-ndf', 1)
    ops.node(0, 0)
    ops.node(1, 0)
    ops.fix(0, 1)
    ops.mass(1, mass)
    material(1, params_mat, points)
    ops.element('twoNodeLink', 1, 0, 1, '-mat', 1, '-dir', 1)

def read_displacements_from_file(file_path):
    """
    从文本文件中读取位移数据
    :param file_path: 文本文件的路径
    :return: 位移数据的NumPy数组
    """
    displacements = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                # 尝试将每行转换为浮点数并添加到列表中
                displacement = float(line.strip())
                displacements.append(displacement)
            except ValueError:
                # 如果转换失败（例如，遇到非数字行），则跳过该行
                continue
    return np.array(displacements)

def static(disp):
    '''
    执行单自由度体系静力分析的函数
    '''
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(1, 1)
    ops.constraints('Plain')
    ops.numberer('Plain')
    ops.system('BandGeneral')
    ops.test('EnergyIncr', 0.000001, 20)
    ops.algorithm('Newton')
    Dincr = disp[1:] - disp[:-1]
    Dincr = np.insert(Dincr, 0, disp[0])
    disp_, force_ = [], []
    for incr in Dincr:
        ops.integrator('DisplacementControl', 1, 1, incr)
        ops.analysis('Static')
        ops.analyze(1)
        disp_.append(ops.nodeDisp(1, 1))
        ops.reactions()
        force_.append(ops.nodeReaction(0, 1))
    disp_, force_ = np.array(disp_), np.array(force_)
    force_[np.isnan(force_)] = 0.
    return disp_, force_


def read_spd(pth):
    '''
    读取滞回曲线数据的函数
    不同的滞回曲线文件读取方式可能不一样
    '''
    NT = 1.
    mm = 1.
    kN = 1000 * NT

    f = open(pth, 'r')
    npts = int(float(f.readlines()[0].split()[0]))
    f.close()

    f = open(pth, 'r')
    content = []
    for line in f.readlines()[1:npts + 1]:
        content.append(list(map(float, line.split())))

    disp, force = [], []
    for i, point in enumerate(content):
        disp.append(point[0])
        force.append(point[1])
    disp, force = np.array(disp), np.array(force)

    f.close()
    return disp * mm, force * kN


def read_points(file_path):
    '''
    读取屈服点、峰值点和极限点数据
    '''
    with open(file_path, 'r') as f:
        content = [list(map(float, line.split())) for line in f.readlines()]

    points = []
    for point in content:
        points.append(point)
    return points


def write_json(pth, content):
    '''
    将优化结果保存为json格式文件的函数
    '''
    with open(pth, 'w') as f:
        f.write(json.dumps(content, indent=4, separators=(',', ': ')))


def cycle_compare(dispExp, forceExp, dispSim, forceSim, labels, saveName = ''):
    '''
    绘制滞回曲线对比图的函数
    '''
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['figure.figsize'] = (5, 4)
    plt.rcParams['figure.dpi'] = 200

    fig, ax = plt.subplots()
    plt.axhline(0, color='k', linewidth=0.8)
    plt.axvline(0, color='k', linewidth=0.8)
    ax.plot(dispExp, forceExp, color='b', label=labels[0])
    ax.plot(dispSim, forceSim, color='r', label=labels[1])

    plt.xlabel('Displacement / mm')
    plt.ylabel('Force / kN')

    plt.grid(True, linestyle='--')
    plt.legend(framealpha=1, fancybox=False, edgecolor='k', loc='upper left')
    plt.tight_layout()

    if saveName:
        plt.savefig(saveName, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def cycle(disp, force, xlabel='Displacement / mm', ylabel='Force / kN', saveName = ''):
    '''
    绘制滞回曲线的函数
    '''
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['figure.figsize'] = (5, 4)
    plt.rcParams['figure.dpi'] = 200

    fig, ax = plt.subplots()
    plt.axhline(0, color='k', linewidth=0.8)
    plt.axvline(0, color='k', linewidth=0.8)
    ax.plot(disp, force, color='#ff5752')

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    plt.grid(True, linestyle='--')
    plt.tight_layout()

    if saveName:
        plt.savefig(saveName, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def _task(path_exp, points):
    '''
    每一步循环中执行的程序
    path_exp: 待识别滞回曲线的文件路径
    points: 已知的屈服点、峰值点和极限点数据
    '''
    current_file_path = os.path.abspath(__file__)
    current_dir_path = os.path.dirname(current_file_path)

    # 识别结果的保存路径
    OptimizationResults = os.path.join(current_dir_path, 'OptimizationResults')
    dir_save = Path(OptimizationResults)
    dir_save.mkdir(parents=True, exist_ok=True)
    name_exp = path_exp.stem
    path_save = dir_save / (name_exp + '.json')

    kN = 1000

    # 如果识别结果已存在，则跳过
    # if path_save.exists():
    #     return None

    # 使程序报错时可以继续识别下一个滞回曲线
    try:
        # 读取滞回曲线并绘制，不同的滞回曲线文件读取方式可能不一样
        disp, force = read_spd(path_exp)
        Figure = os.path.join(current_dir_path, 'Figure')
        dir_figure = Path(Figure)
        dir_figure.mkdir(parents=True, exist_ok=True)
        cycle(disp, force / kN, saveName=dir_figure / (name_exp + '.png'))

        # 识别滞回模型参数
        # 优化算法为迭代式。pop_size越大，每轮迭代时间越长。epoch为最大迭代次数。early_stop表示连续10轮优化结果没有改善时停止迭代
        config = {'pop_size': 50, 'epoch': 1000, 'early_stop': 10}
        start = time.time()
        x, error = optimize(disp, force, 'Hysteretic', 'ARO', config, points)
        end = time.time()

        # 保存优化结果
        result = {
            'x': [round(i, 3) for i in x],
            'error': error,
            'time': end - start
        }
        write_json(path_save, result)

        # 绘制滞回曲线对比图
        SDOF(Hysteretic, x, points, 1)
        current_file_path = os.path.abspath(__file__)
        current_dir_path = os.path.dirname(current_file_path)
        file_path =  os.path.join(current_dir_path, 'path.txt')
        displacements = read_displacements_from_file(file_path)
        disp_opt, force_opt = static(displacements)
        force_opt = -force_opt
        # disp_opt, force_opt = opt.simulation(x)
        FigureOptim = os.path.join(current_dir_path, 'FigureOptim')
        dir_figure = Path(FigureOptim)
        dir_figure.mkdir(parents=True, exist_ok=True)
        cycle_compare(disp, force / kN, disp_opt, force_opt / kN,
                      ['Simulation result', 'Optimization result'], dir_figure / (name_exp + '.png'))

        # 绘制单独的优化后滞回曲线图
        FigureOptimSingle = os.path.join(current_dir_path, 'FigureOptimSingle')
        dir_figure_optim = Path(FigureOptimSingle)
        dir_figure_optim.mkdir(parents=True, exist_ok=True)
        cycle(disp_opt, force_opt / kN, saveName=dir_figure_optim / (name_exp + '_optim.png'))
        data_file_path = dir_figure_optim / (name_exp + '_data.txt')
        np.savetxt(data_file_path, np.column_stack((disp_opt, force_opt / kN)), fmt='%f', delimiter=' ') 

    except Exception as e:
        print(str(e))

if __name__ == '__main__':
    # 存放滞回曲线数据的文件夹
    current_file_path = os.path.abspath(__file__)
    current_dir_path = os.path.dirname(current_file_path)
    hysteretic_curves_dir = os.path.join(current_dir_path, 'HystereticCurves')
    f_dir = os.path.join(current_dir_path, 'F')
    dir_exp = Path(hysteretic_curves_dir)
    dir_points = Path(f_dir)

    # 遍历每个滞回曲线文件执行循环任务
    for path_exp in dir_exp.iterdir():
        # 遍历读取每个点数据文件，并将数据组织成 points 列表
        points = []
        for file_path in dir_points.iterdir():
            points.extend(read_points(file_path))
        _task(path_exp, points)
