"""
生成测试 CSV 数据
模拟 iOS App 导出的 Raw CSV 和 Feedback CSV
运行: python generate_test_data.py
"""
import numpy as np
import pandas as pd
import uuid
import os

np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SESSION_ID = str(uuid.uuid4())
DURATION = 60.0       # 60 秒的 session
SAMPLE_RATE = 100     # 100 Hz
NUM_ACTIONS = 25      # 25 个动作
WINDOW_SIZE = 0.45    # 窗口半径 (秒)

print(f"Session ID: {SESSION_ID}")
print(f"生成 {DURATION}s, {SAMPLE_RATE}Hz 的测试数据...")

# ---- 1. 生成 Raw IMU CSV ----
n_samples = int(DURATION * SAMPLE_RATE)
t = np.linspace(0, DURATION, n_samples)
base_time = 1708180000.0  # 模拟 unix timestamp

# 背景噪声
acc_noise = 0.05
gyro_noise = 0.02

# 基础信号
userAccelX = np.random.normal(0, acc_noise, n_samples)
userAccelY = np.random.normal(0, acc_noise, n_samples)
userAccelZ = np.random.normal(0, acc_noise, n_samples)
rotationRateX = np.random.normal(0, gyro_noise, n_samples)
rotationRateY = np.random.normal(0, gyro_noise, n_samples)
rotationRateZ = np.random.normal(0, gyro_noise, n_samples)

# 在特定时间点注入动作峰值
action_times = np.sort(np.random.uniform(2, DURATION - 2, NUM_ACTIONS))
action_qualities = []

for i, at in enumerate(action_times):
    idx = int(at * SAMPLE_RATE)
    half_w = int(WINDOW_SIZE * SAMPLE_RATE)
    start = max(0, idx - half_w)
    end = min(n_samples, idx + half_w)

    # Good 动作: 高加速度、规律的模式
    # Bad 动作: 不规则、低加速度
    is_good = np.random.random() > 0.35  # 65% good
    quality = "good" if is_good else "bad"
    action_qualities.append(quality)

    if is_good:
        mag = np.random.uniform(3.0, 6.0)
        # 平滑的钟形曲线
        w = end - start
        bell = mag * np.exp(-0.5 * ((np.arange(w) - w//2) / (w/6))**2)
        userAccelX[start:end] += bell * np.random.uniform(0.3, 0.8)
        userAccelY[start:end] += bell * np.random.uniform(0.3, 0.8)
        userAccelZ[start:end] += bell * np.random.uniform(0.5, 1.0)
        rotationRateX[start:end] += bell * 0.3
        rotationRateY[start:end] += bell * 0.5
    else:
        mag = np.random.uniform(1.5, 3.5)
        # 不规则的噪声
        w = end - start
        noise = mag * np.random.normal(0, 0.5, w)
        userAccelX[start:end] += noise * 0.5
        userAccelY[start:end] += noise * 0.3
        userAccelZ[start:end] += noise * 0.8
        rotationRateX[start:end] += np.random.normal(0, 0.3, w)

raw_df = pd.DataFrame({
    "session_id": SESSION_ID,
    "session_type": "create",
    "seconds_elapsed": [f"{x:.6f}" for x in t],
    "time": [f"{base_time + x:.6f}" for x in t],
    "accelerationX": np.random.normal(0, 0.1, n_samples),
    "accelerationY": np.random.normal(0, 0.1, n_samples),
    "accelerationZ": np.random.normal(9.8, 0.1, n_samples),
    "userAccelX": userAccelX,
    "userAccelY": userAccelY,
    "userAccelZ": userAccelZ,
    "gravityX": np.zeros(n_samples),
    "gravityY": np.zeros(n_samples),
    "gravityZ": np.full(n_samples, 9.80665),
    "rotationRateX": rotationRateX,
    "rotationRateY": rotationRateY,
    "rotationRateZ": rotationRateZ,
    "quaternionW": np.ones(n_samples),
    "quaternionX": np.zeros(n_samples),
    "quaternionY": np.zeros(n_samples),
    "quaternionZ": np.zeros(n_samples),
})

raw_path = os.path.join(OUTPUT_DIR, f"{SESSION_ID}_create_test.csv")
raw_df.to_csv(raw_path, index=False)
print(f"Raw CSV: {raw_path} ({len(raw_df)} rows)")

# ---- 2. 生成 Feedback CSV ----
feedback_rows = []

for i, (at, quality) in enumerate(zip(action_times, action_qualities)):
    t_peak = base_time + at
    t_start = t_peak - WINDOW_SIZE
    t_end = t_peak + WINDOW_SIZE

    # 提取窗口数据计算特征
    idx = int(at * SAMPLE_RATE)
    half_w = int(WINDOW_SIZE * SAMPLE_RATE)
    start = max(0, idx - half_w)
    end = min(n_samples, idx + half_w)

    channels = {
        "accX": userAccelX[start:end],
        "accY": userAccelY[start:end],
        "accZ": userAccelZ[start:end],
        "accMag": np.sqrt(userAccelX[start:end]**2 + userAccelY[start:end]**2 + userAccelZ[start:end]**2),
        "gyroX": rotationRateX[start:end],
        "gyroY": rotationRateY[start:end],
        "gyroZ": rotationRateZ[start:end],
        "gyroMag": np.sqrt(rotationRateX[start:end]**2 + rotationRateY[start:end]**2 + rotationRateZ[start:end]**2),
    }

    row = {
        "session_id": SESSION_ID,
        "action_index": i + 1,
        "t_peak": f"{t_peak:.6f}",
        "t_start": f"{t_start:.6f}",
        "t_end": f"{t_end:.6f}",
        "ml_classification": "forehand",
        "ml_quality": quality,
        "manual_quality": quality,
    }

    # 40 维特征
    for ch_name, ch_data in channels.items():
        if len(ch_data) == 0:
            ch_data = np.array([0.0])
        row[f"mean_{ch_name}"] = float(np.mean(ch_data))
        row[f"std_{ch_name}"] = float(np.std(ch_data))
        row[f"max_{ch_name}"] = float(np.max(np.abs(ch_data)))
        row[f"min_{ch_name}"] = float(np.min(ch_data))
        # Simpson 积分近似
        if len(ch_data) >= 3:
            dx = WINDOW_SIZE * 2 / len(ch_data)
            row[f"simpson_{ch_name}"] = float(np.trapz(ch_data, dx=dx))
        else:
            row[f"simpson_{ch_name}"] = 0.0

    row["isoTime"] = "2024-02-17T14:30:00Z"
    feedback_rows.append(row)

feedback_df = pd.DataFrame(feedback_rows)
fb_path = os.path.join(OUTPUT_DIR, f"{SESSION_ID}_feedback_test.csv")
feedback_df.to_csv(fb_path, index=False)
print(f"Feedback CSV: {fb_path} ({len(feedback_df)} rows)")

# 统计
good_n = sum(1 for q in action_qualities if q == "good")
bad_n = sum(1 for q in action_qualities if q == "bad")
print(f"\n统计: {NUM_ACTIONS} 动作, Good: {good_n}, Bad: {bad_n}")
print(f"\n测试文件已生成到 {OUTPUT_DIR}/")
print("用这两个文件在 Upload 页面上传测试！")
