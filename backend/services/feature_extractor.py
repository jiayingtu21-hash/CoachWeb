"""
40 维特征提取服务
从 IMU 窗口数据提取统计特征
"""
import numpy as np
import pandas as pd
from typing import List


def extract_features(window: pd.DataFrame) -> np.ndarray:
    """
    从窗口提取 40 维特征

    特征结构:
    - Accelerometer (x, y, z, mag) × 5 features = 20
    - Gyroscope (x, y, z, mag) × 5 features = 20

    5 features per axis:
    1. Mean (均值)
    2. Std (标准差)
    3. Max (峰值)
    4. RMS (均方根)
    5. Zero-crossing rate (过零率)

    Args:
        window: 时间窗口内的 IMU DataFrame

    Returns:
        40 维特征向量
    """
    features = []

    # 加速度特征 (20 维)
    for col in ['userAccelX', 'userAccelY', 'userAccelZ', 'accMag']:
        if col not in window.columns:
            raise ValueError(f"Column '{col}' not found in window")
        data = window[col].values
        features.extend(_compute_stats(data))

    # 陀螺仪特征 (20 维)
    for col in ['rotationRateX', 'rotationRateY', 'rotationRateZ', 'gyroMag']:
        if col not in window.columns:
            raise ValueError(f"Column '{col}' not found in window")
        data = window[col].values
        features.extend(_compute_stats(data))

    return np.array(features, dtype=np.float32)


def _compute_stats(data: np.ndarray) -> List[float]:
    """
    计算 5 个统计特征

    Args:
        data: 时序数据

    Returns:
        [mean, std, max, rms, zcr]
    """
    # 处理空数组
    if len(data) == 0:
        return [0.0, 0.0, 0.0, 0.0, 0.0]

    return [
        float(np.mean(data)),                           # Mean
        float(np.std(data)),                            # Std
        float(np.max(np.abs(data))),                    # Max (绝对值)
        float(np.sqrt(np.mean(data**2))),              # RMS
        float(np.sum(np.diff(np.sign(data)) != 0))     # Zero-crossing rate
    ]


def batch_extract_features(
    raw_df: pd.DataFrame,
    peaks: List[dict],
    window_size: float
) -> tuple[np.ndarray, List[dict]]:
    """
    批量提取特征

    Args:
        raw_df: Raw IMU DataFrame
        peaks: 峰值列表
        window_size: 窗口半径（秒）

    Returns:
        (features_matrix, valid_peaks)
        - features_matrix: (n_actions, 40)
        - valid_peaks: 有效的峰值列表（过滤掉窗口数据不足的）
    """
    from .csv_parser import segment_window

    features_list = []
    valid_peaks = []

    for peak in peaks:
        window = segment_window(raw_df, peak['time'], window_size)

        # 确保窗口有足够数据（至少 10 个采样点）
        if len(window) >= 10:
            try:
                features = extract_features(window)
                features_list.append(features)
                valid_peaks.append(peak)
            except Exception as e:
                print(f"[FeatureExtractor] Failed to extract features for peak at {peak['time']}: {e}")
                continue

    if len(features_list) == 0:
        return np.array([]), []

    return np.vstack(features_list), valid_peaks


def get_feature_names() -> List[str]:
    """
    返回 40 个特征的名称（用于模型解释）

    Returns:
        特征名称列表
    """
    names = []

    # 加速度
    for axis in ['AccX', 'AccY', 'AccZ', 'AccMag']:
        for stat in ['Mean', 'Std', 'Max', 'RMS', 'ZCR']:
            names.append(f'{axis}_{stat}')

    # 陀螺仪
    for axis in ['GyroX', 'GyroY', 'GyroZ', 'GyroMag']:
        for stat in ['Mean', 'Std', 'Max', 'RMS', 'ZCR']:
            names.append(f'{axis}_{stat}')

    return names
