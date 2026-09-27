import numpy as np

# 读取文件中的数据
data = []
with open('path1.txt', 'r') as file:
    for line in file:
        data.append(float(line.strip()))

# 将数据转换为numpy数组
data_array = np.array(data)

# 设置插值数量
num_interpolation = 4

# 初始化结果数组
result = []

# 进行插值
for i in range(len(data_array) - 1):
    start = data_array[i]
    end = data_array[i + 1]
    # 使用numpy的linspace进行等距插值
    interpolated_values = np.linspace(start, end, num_interpolation + 2)[1:]  # 排除首尾值，只取中间的插值
    result.extend(interpolated_values)

# 添加最后一个数据点（因为最后一个点后面没有需要插值的点了）
result.append(data_array[-1])

# 将结果转换为numpy数组（可选）
result_array = np.array(result)

# 打印结果或保存到文件
print("Interpolated values:")
print(result_array)

# 如果需要保存到文件，可以使用以下代码
with open('interpolated_pathx.txt', 'w') as file:
    for value in result_array:
        file.write(f"{value}\n")