import os
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d


# 定义文件夹路径
current_file_path = os.path.abspath(__file__)
current_dir_path = os.path.dirname(current_file_path)
f_folder = os.path.join(current_dir_path, 'F')
optimization_results_folder = os.path.join(current_dir_path, 'OptimizationResults')

# 如果输出文件夹和图像文件夹不存在，则创建它们
for folder in [f_folder, optimization_results_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# 获取F文件夹中的txt文件
txt_files = [f for f in os.listdir(f_folder) if f.endswith('.txt')]
if not txt_files:
    raise FileNotFoundError(f"No txt file found in {f_folder}")
txt_file_path = os.path.join(f_folder, txt_files[0])  # 取第一个txt文件

# 获取OptimizationResults文件夹中的json文件
json_files = [f for f in os.listdir(optimization_results_folder) if f.endswith('.json')]
if not json_files:
    raise FileNotFoundError(f"No json file found in {optimization_results_folder}")
json_file_path = os.path.join(optimization_results_folder, json_files[0])  # 取第一个json文件

# 读取txt文件中的数据
with open(txt_file_path, 'r') as txt_file:
    txt_data = txt_file.readlines()

# 将txt文件中的数据转换为一个列表
txt_values = []
for line in txt_data:
    values = line.strip().split()
    txt_values.extend(values)

# 读取json文件中的数据
with open(json_file_path, 'r') as json_file:
    json_data = json.load(json_file)

# 获取json文件中的x值
x_values = json_data['x']

# 将x值转换为字符串列表
x_values_str = [str(value) for value in x_values]

# 合并txt数据和x值
merged_data = txt_values + x_values_str

# 将合并后的数据写入一个新的txt文件
current_file_path = os.path.abspath(__file__)
current_dir_path = os.path.dirname(current_file_path)
output_file_path = os.path.join(current_dir_path, 'parameters.txt')
with open(output_file_path, 'w') as output_file:
    output_file.write(' '.join(merged_data))

print(f"数据已合并并保存到 {output_file_path}")