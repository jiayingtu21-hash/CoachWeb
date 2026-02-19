"""
CSV 文件解析服务
处理从 App 导出的 raw IMU 和 feedback CSV
"""
import pandas as pd
import numpy as np
from io import StringIO
from typing import List, Dict, Optional


def parse_raw_csv(file_content: str) -> pd.DataFrame:
    """
    解析 raw IMU CSV

    Args:
        file_content: CSV 文件内容（字符串）

    Returns:
        包含 magnitude 的 DataFrame
    """
    df = pd.read_csv(StringIO(file_content))

    # 计算加速度 magnitude
    df['accMag'] = np.sqrt(
        df['userAccelX']**2 +
        df['userAccelY']**2 +
        df['userAccelZ']**2
    )

    # 计算陀螺仪 magnitude
    df['gyroMag'] = np.sqrt(
        df['rotationRateX']**2 +
        df['rotationRateY']**2 +
        df['rotationRateZ']**2
    )

    return df


def parse_feedback_csv(file_content: str) -> pd.DataFrame:
    """
    解析 feedback CSV

    Args:
        file_content: CSV 文件内容

    Returns:
        Feedback DataFrame
    """
    df = pd.read_csv(StringIO(file_content))

    # 验证必需列
    required_cols = ['session_id', 'action_index', 't_peak', 't_start', 't_end']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    return df


def detect_peaks(
    df: pd.DataFrame,
    threshold: float = 2.2,
    cooldown: float = 0.45
) -> List[Dict]:
    """
    峰值检测（复刻 Swift 逻辑）

    Args:
        df: Raw IMU DataFrame（必须包含 'time' 和 'accMag' 列）
        threshold: 加速度阈值（m/s²）
        cooldown: 冷却时间（秒）

    Returns:
        峰值列表，每个峰值包含 index, time, magnitude
    """
    if 'time' not in df.columns or 'accMag' not in df.columns:
        raise ValueError("DataFrame must contain 'time' and 'accMag' columns")

    peaks = []
    last_peak_time = -cooldown

    for i, row in df.iterrows():
        if row['accMag'] > threshold:
            time_diff = row['time'] - last_peak_time
            if time_diff >= cooldown:
                peaks.append({
                    'index': int(i),
                    'time': float(row['time']),
                    'magnitude': float(row['accMag'])
                })
                last_peak_time = row['time']

    return peaks


def segment_window(
    df: pd.DataFrame,
    peak_time: float,
    window_size: float
) -> pd.DataFrame:
    """
    提取峰值前后的时间窗口

    Args:
        df: Raw IMU DataFrame
        peak_time: 峰值时间
        window_size: 窗口半径（秒）

    Returns:
        窗口内的 DataFrame
    """
    t_start = peak_time - window_size
    t_end = peak_time + window_size

    window = df[(df['time'] >= t_start) & (df['time'] <= t_end)].copy()

    return window


def validate_csv_format(df: pd.DataFrame, csv_type: str) -> tuple[bool, Optional[str]]:
    """
    验证 CSV 格式是否正确

    Args:
        df: DataFrame
        csv_type: 'raw' 或 'feedback'

    Returns:
        (是否有效, 错误信息)
    """
    if csv_type == 'raw':
        required = [
            'session_id', 'session_type', 'time',
            'userAccelX', 'userAccelY', 'userAccelZ',
            'rotationRateX', 'rotationRateY', 'rotationRateZ'
        ]
    elif csv_type == 'feedback':
        required = [
            'session_id', 'action_index', 't_peak', 't_start', 't_end',
            'ml_classification', 'ml_quality', 'manual_quality'
        ]
    else:
        return False, f"Unknown CSV type: {csv_type}"

    missing = [col for col in required if col not in df.columns]
    if missing:
        return False, f"Missing columns: {', '.join(missing)}"

    return True, None
