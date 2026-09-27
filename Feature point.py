import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution
from scipy.interpolate import interp1d
from scipy.optimize import minimize
from scipy.optimize import fsolve, root


# 定义文件夹路径
current_file_path = os.path.abspath(__file__)
current_dir_path = os.path.dirname(current_file_path)
input_folder = os.path.join(current_dir_path, "Hysteretic")
output_folder = os.path.join(current_dir_path, "backbone")
figure_folder = os.path.join(current_dir_path, "Figure")
fcr_folder = os.path.join(current_dir_path, "F")

# 如果输出文件夹和图像文件夹不存在，则创建它们
for folder in [output_folder, figure_folder, fcr_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 批量处理文件夹中的每个 TXT 文件
for filename in os.listdir(input_folder):
    if filename.endswith(".txt"):
        # 构建完整的文件路径
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        figure_path = os.path.join(figure_folder, f"{os.path.splitext(filename)[0]}.png")
        fcr_path = os.path.join(fcr_folder, filename)

        # 读取数据
        with open(input_path, "r") as file:
            data = file.readlines()

        lit = []
        EndCirclePoints = []

        for d in data:
            tmpd = d.split()
            row_data = [float(val) for val in tmpd]  # 将字符串转换为浮点数，并保持每行的数据结构
            lit.append(row_data)

        LineNum = len(lit)  # 使用第一行的长度作为数据的列数
        outdata = np.array(lit)

        # 找到各级循环的分割点位置
        for i in range(2, LineNum):
            if (outdata[i, 0] * outdata[i - 1, 0] <= 0) and (outdata[i - 1, 0] < 0):
                EndCirclePoints.append(i)

        # 检查是否存在不完整的滞回环
        LoopNum = len(EndCirclePoints) + 1 if EndCirclePoints[-1] < LineNum else len(EndCirclePoints)

        # 分割各个滞回环
        LoopCircles = [outdata[0:EndCirclePoints[0], :]]
        for k in range(1, LoopNum):
            if k < LoopNum - 1:
                LoopCircles.append(outdata[EndCirclePoints[k - 1]:EndCirclePoints[k], :])
            else:
                LoopCircles.append(outdata[EndCirclePoints[k - 1]:LineNum, :])

        # 提取各个滞回环的荷载骨架曲线点
        FramePointsPositive = []
        FramePointsNegative = []
        for A in LoopCircles:
            LineMax = np.argmax(A[:, 1])
            LineMin = np.argmin(A[:, 1])
            FramePointsPositive.append(A[LineMax, :])
            FramePointsNegative.append(A[LineMin, :])

        # 比较最大位移，删除骨架曲线中同一荷载级的较小骨架点
        for k in range(len(LoopCircles) - 1, 0, -1):
            A = LoopCircles[k]
            B = LoopCircles[k - 1]
            MaxA = np.max(A[:, 1])
            MaxB = np.max(B[:, 1])
            MinA = np.min(A[:, 1])
            MinB = np.min(B[:, 1])
            if abs(MaxA - MaxB) < 4:
                if MaxA < MaxB:
                    FramePointsPositive.pop(k)
                else:
                    FramePointsPositive.pop(k - 1)
            if abs(MinA - MinB) < 4:
                if MinA < MinB:
                    FramePointsNegative.pop(k - 1)
                else:
                    FramePointsNegative.pop(k)

        # 合并正负骨架点并按位移值排序
        FramePoints = np.vstack((FramePointsPositive, FramePointsNegative))
        FramePoints = FramePoints[np.abs(FramePoints[:, 0]) >= 0.1]  # 将骨架曲线中横坐标距离原点小于0.1的数据点删除
        FramePoints_with_origin = np.vstack([[0, 0], FramePoints])
        FramePoints_with_origin = FramePoints_with_origin[FramePoints_with_origin[:, 0].argsort()]

        # 删除满足条件的点
        # 找到峰值点（纵坐标最大的点）的横坐标绝对值
        peak_index = np.argmax(FramePoints_with_origin[:, 1])
        peak_x_abs = np.abs(FramePoints_with_origin[peak_index, 0])
        indices_to_keep = []
        for i in range(len(FramePoints_with_origin)):
            current_abs_x = np.abs(FramePoints_with_origin[i, 0])
            # 若当前点横坐标绝对值小于等于峰值点横坐标绝对值，直接保留
            if current_abs_x <= peak_x_abs / 2:
                indices_to_keep.append(i)
            else:
                if i == 0 or i == len(FramePoints_with_origin) - 1:
                    # 第一个和最后一个点直接保留
                    indices_to_keep.append(i)
                else:
                    current_abs_y = np.abs(FramePoints_with_origin[i, 1])
                    left_abs_y = np.abs(FramePoints_with_origin[i - 1, 1])
                    right_abs_y = np.abs(FramePoints_with_origin[i + 1, 1])
                    # 若当前点纵坐标绝对值不小于左右相邻点的纵坐标绝对值，则保留
                    if current_abs_y >= left_abs_y or current_abs_y >= right_abs_y:
                        indices_to_keep.append(i)
        FramePoints_with_origin = FramePoints_with_origin[indices_to_keep]

        # 将结果写入文件
        np.savetxt(output_path, FramePoints_with_origin, delimiter='\t', fmt='%.2f')
        print(FramePoints_with_origin)
        # plt.plot(FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1], 'k', label='Backbone Curve')
        # plt.show()
        # 读取骨架曲线数据并绘制其每一段的导数值连成的曲线
        positive_points = FramePoints_with_origin[FramePoints_with_origin[:, 0] >= 0]
        negative_points = FramePoints_with_origin[FramePoints_with_origin[:, 0] <= 0]


        #####峰值点#####
        #####峰值点#####
        #####峰值点#####

        max_y = np.max(FramePoints_with_origin[:, 1])
        min_y = np.min(FramePoints_with_origin[:, 1])
        max_y_point = FramePoints_with_origin[FramePoints_with_origin[:, 1] == max_y][0]
        min_y_point = FramePoints_with_origin[FramePoints_with_origin[:, 1] == min_y][0]
        x_avg = (np.abs(max_y_point[0]) + np.abs(min_y_point[0])) / 2
        y_avg = (np.abs(max_y_point[1]) + np.abs(min_y_point[1])) / 2
        peak_point_positive = np.array([x_avg, y_avg]).flatten()
        peak_point_negative = peak_point_positive * -1
        peak_point_negative = peak_point_negative.flatten()




        #####开裂点#####
        #####开裂点#####
        #####开裂点#####

        ## 求等效面积
        # 生成正负峰值点之间更密集的 x 值用于插值
        x_interp = np.linspace(-peak_point_positive[0], peak_point_positive[0], 1000)
        # 进行线性插值
        y_interp = np.interp(x_interp, FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1])
        # 分离正负部分
        positive_mask = y_interp >= 0
        negative_mask = y_interp < 0
        x_positive = x_interp[positive_mask]
        y_positive = y_interp[positive_mask]
        x_negative = x_interp[negative_mask]
        y_negative = y_interp[negative_mask]
        # 分别计算正负部分的积分面积
        area_positive = np.trapezoid(y_positive, x_positive)
        area_negative = np.abs(np.trapezoid(y_negative, x_negative))
        # 总面积
        total_area = area_positive + area_negative

        ## 求拐点
        # 找到 y 坐标最大点的索引
        max_y_index = np.argmax(FramePoints_with_origin[:, 1])
        # x0 是 y 坐标最大点的左侧相邻点的横坐标
        x0 = FramePoints_with_origin[:, 0][max_y_index - 1]
        # 定义 n 的值，这里设为 1000，可以根据需要调整
        n = 1000
        # 在 (0, x0) 之间等间距取 n 个 x 坐标
        x_new = np.linspace(0, x0, n)
        # 线性插值得到对应的 y 坐标
        y_new = np.interp(x_new, FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1])
        # 计算每一段折线的斜率
        slopes = np.diff(y_new) / np.diff(x_new)
        # 计算斜率的变化
        slope_changes = -1 * np.diff(slopes)
        # 找到斜率变化最大点的索引
        max_slope_change_index = np.argmax(slope_changes)
        # 对应的横坐标
        max_slope_change_x = x_new[max_slope_change_index + 1]
        # 提取折线上横坐标为 max_slope_change_x 和 -1 * max_slope_change_x 的纵坐标
        y_max_slope = np.interp(max_slope_change_x, FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1])
        y_neg_max_slope = np.interp(-1 * max_slope_change_x, FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1])
        # 计算纵坐标绝对值的平均值
        avg_y = (np.abs(y_max_slope) + np.abs(y_neg_max_slope)) / 2
        # 记录新的点
        inflection_point = (max_slope_change_x, avg_y)
        inflection_point_x = max_slope_change_x
        inflection_point_y = avg_y

        def find_point(inflection_x, inflection_y, peak_x, peak_y, target_area):
            k = inflection_y / inflection_x  # 拐点斜率
            # 分解为两步求解（先满足直线约束，再求解面积）
            def area_function(x):
                y = k * x
                area_triangle = 0.5 * x * y
                area_trapezoid = 0.5 * (y + d) * (c - x)
                return 2 * (area_triangle + area_trapezoid) - target_area
            # 使用二分法寻找初始解范围
            x_min = 1e-6  # 避免x=0
            x_max = peak_x - 1e-6  # 避免x=c
            # 检查函数符号变化
            if np.sign(area_function(x_min)) == np.sign(area_function(x_max)):
                raise ValueError("No solution in the given range")
            # 使用二分法找到初始解
            x_initial = np.zeros(100)
            for i in range(100):
                x_mid = (x_min + x_max) / 2
                f_mid = area_function(x_mid)
                if f_mid < 0:
                    x_min = x_mid
                else:
                    x_max = x_mid
                x_initial[i] = x_mid
            # 选择最接近的解作为初始猜测
            x0 = x_initial[-1]
            y0 = k * x0
            # 使用更鲁棒的求解器
            def objective(xy):
                inflection_x, inflection_y = xy
                return [2*(0.5*inflection_x*inflection_y + 0.5*(inflection_y + peak_y)*(peak_x - inflection_x)) - target_area,
                        inflection_y - k*inflection_x]
            # 尝试不同的求解方法
            # 求解器选项映射
            solver_options = {
                'hybr': {'maxfev': 1000, 'xtol': 1e-8},  # 使用maxfev代替maxiter
                'lm': {'maxiter': 1000, 'xtol': 1e-8},
                'broyden1': {'maxiter': 1000, 'xtol': 1e-8},
                'broyden2': {'maxiter': 1000, 'xtol': 1e-8}
            }
            import warnings
            warnings.filterwarnings("ignore", message="Unknown solver options: maxiter")
            solution = None
            for method in solver_options:
                try:
                    solution = root(objective, [x0, y0], method=method,
                                    options={'maxiter': 1000, 'xtol': 1e-8})
                    if solution.success:
                        break
                except:
                    continue
            if solution is None or not solution.success:
                raise RuntimeError("Solution not found")
            return solution.x
        # 参数定义
        a = inflection_point_x                # 拐点的x坐标
        b = inflection_point_y                # 拐点的y坐标
        c = peak_point_positive[0]            # 峰值点的x坐标
        d = peak_point_positive[1]            # 峰值点的y坐标
        target_area = total_area              # 目标面积
        # 求解
        crack_x, crack_y = find_point(a, b, c, d, target_area)
        crack_point_positive = np.array([crack_x, crack_y]).flatten()
        crack_point_negative = crack_point_positive * -1
        crack_point_negative = crack_point_negative.flatten()



        #####极限点#####
        #####极限点#####
        #####极限点#####
        
        ## 求等效面积
        # 计算 x=peak_point_positive[0] 到 x=FramePoints_with_origin[-1,0] 之间的积分面积
        x_dense_1 = np.linspace(peak_point_positive[0], FramePoints_with_origin[-1, 0], 1000)
        y_dense_1 = np.interp(x_dense_1, FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1])
        integral_1 = np.trapezoid(y_dense_1, x_dense_1)
        area_1 = np.abs(integral_1)
        # 计算 x=FramePoints_with_origin[0,0] 到 x=-1*peak_point_positive[0] 之间的积分面积
        x_dense_2 = np.linspace(FramePoints_with_origin[0, 0], -1 * peak_point_positive[0], 1000)
        y_dense_2 = np.interp(x_dense_2, FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1])
        integral_2 = np.trapezoid(y_dense_2, x_dense_2)
        area_2 = np.abs(integral_2)
        # 求和
        total_area = area_1 + area_2

        # 计算 ultimate_point_positive 的纵坐标
        pos_points = FramePoints_with_origin[FramePoints_with_origin[:, 0] > peak_point_positive[0]]
        neg_points = FramePoints_with_origin[FramePoints_with_origin[:, 0] < -1 * peak_point_positive[0]]
        y_min_abs = np.abs(np.min(pos_points[:, 1]))
        y_max_abs = np.abs(np.max(neg_points[:, 1]))
        ultimate_y = (y_min_abs + y_max_abs) / 2

        # 定义计算折线积分面积的函数
        def calculate_polygon_area(peak_p, ultimate_p, horizon_p):
            peak_p = np.array(peak_p).flatten()
            ultimate_p = np.array(ultimate_p).flatten()
            horizon_p = np.array(horizon_p).flatten()
            points = np.array([peak_p, ultimate_p, horizon_p])
            x = points[:, 0]
            y = points[:, 1]
            x_dense = np.linspace(x[0], x[-1], 1000)
            y_dense = np.interp(x_dense, x, y)
            integral = np.trapezoid(y_dense, x_dense)
            return np.abs(integral)
        
        # 定义目标函数，用于最小化差值
        def objective_function(x_value):
            x_value =  x_value.item()  # 确保传入的是单个数值
            ultimate_point_positive = [x_value, ultimate_y]
            ultimate_point_negative = [-x_value, -ultimate_y]
            horizon_pos = [FramePoints_with_origin[-1, 0], ultimate_y]
            horizon_neg = [FramePoints_with_origin[0, 0], -ultimate_y]
            area_pos = calculate_polygon_area(peak_point_positive, ultimate_point_positive, horizon_pos)
            area_neg = calculate_polygon_area(horizon_neg, ultimate_point_negative, peak_point_negative)
            area_sum = area_pos + area_neg
            return (area_sum - total_area) ** 2
        # 初始猜测值（改为标量）
        initial_guess = (peak_point_positive[0] + FramePoints_with_origin[-1, 0]) / 2
        # 定义约束条件
        bounds_ultimate = [(peak_point_positive[0], FramePoints_with_origin[-1, 0])]
        # 使用 minimize 函数进行优化，并传入约束条件
        result = minimize(objective_function, initial_guess, bounds=bounds_ultimate)
        # 得到最终的 x 值
        final_x = result.x[0]
        ultimate_point_positive = np.array([final_x, ultimate_y]).flatten()
        ultimate_point_negative = ultimate_point_positive * -1
        ultimate_point_negative = ultimate_point_negative.flatten()



        # 保存特征点数据
        points = np.vstack((crack_point_positive, peak_point_positive, ultimate_point_positive, crack_point_negative, peak_point_negative, ultimate_point_negative))
        np.savetxt(fcr_path, points, delimiter='\t', fmt='%.2f')

        # 绘图并保存到图像文件夹中
        plt.plot(outdata[:, 0], outdata[:, 1], 'r', label='Hysteresis curve')
        plt.plot(FramePoints_with_origin[:, 0], FramePoints_with_origin[:, 1], 'k', label='Backbone Curve')
        plt.scatter(crack_point_positive[0], crack_point_positive[1], color='green', marker='o', s=50, zorder=5,
                    label='Crack Point Positive')  # 标记正半轴开裂点
        plt.scatter(crack_point_negative[0], crack_point_negative[1], color='purple', marker='o', s=50, zorder=5,
                    label='Crack Point Negative')  # 标记负半轴开裂点
        plt.scatter(peak_point_positive[0], peak_point_positive[1], color='c', marker='o', s=50, zorder=5,
                    label='Peak Point Positive')  # 标记正半轴峰值点
        plt.scatter(peak_point_negative[0], peak_point_negative[1], color='magenta', marker='o', s=50, zorder=5,
                    label='Peak Point Negative')  # 标记负半轴峰值点
        plt.scatter(ultimate_point_positive[0], ultimate_point_positive[1], color='orange', marker='o', s=50, zorder=5,
                    label='Ultimate_point_positive')  # 标记正半轴极限点
        plt.scatter(ultimate_point_negative[0], ultimate_point_negative[1], color='blue', marker='o', s=50, zorder=5,
                    label='Ultimate_point_negative')  # 标记负半轴极限点
        # plt.scatter(0, 0, color='black', marker='o', label='Origin')  # 添加原点

        # 绘制六个特征点的连线
        feature_points = [ultimate_point_negative, peak_point_negative, crack_point_negative,  
                          crack_point_positive, peak_point_positive, ultimate_point_positive]
        feature_points = np.array(feature_points)
        plt.plot(feature_points[:, 0], feature_points[:, 1], 'b--', label='Feature Points Connection')

        plt.title(f'Backbone Curve for {filename}')
        plt.xlabel('Displacement(mm)')
        plt.ylabel('Force(kN)')
        plt.legend()
        plt.tight_layout()
        plt.savefig(figure_path)  # 保存图像
        plt.clf()  # 清空当前图像，以便处理下一个文件

