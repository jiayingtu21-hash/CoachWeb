"""
数据可视化路由
Raw CSV 数据仍从文件系统读取，feedback 数据从 SQLite 读取
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import pandas as pd
from io import StringIO

from sqlalchemy.orm import Session as DBSession
from db.database import get_db
from services import storage

router = APIRouter()


@router.get("/raw-data/{session_id}")
async def get_raw_data(session_id: str, sample_rate: Optional[int] = None):
    """获取 raw IMU 数据用于时序图"""
    csv_content = storage.load_csv(session_id, "raw.csv")
    if not csv_content:
        raise HTTPException(status_code=404, detail="Raw CSV not found")

    df = pd.read_csv(StringIO(csv_content))

    if sample_rate and sample_rate > 0 and len(df) > sample_rate:
        step = max(1, len(df) // sample_rate)
        df = df.iloc[::step]

    cols = ['time', 'userAccelX', 'userAccelY', 'userAccelZ',
            'rotationRateX', 'rotationRateY', 'rotationRateZ']
    available_cols = [c for c in cols if c in df.columns]

    if all(c in df.columns for c in ['userAccelX', 'userAccelY', 'userAccelZ']):
        df['accMag'] = (df['userAccelX']**2 + df['userAccelY']**2 + df['userAccelZ']**2)**0.5
        available_cols.append('accMag')

    if 'seconds_elapsed' in df.columns:
        available_cols.append('seconds_elapsed')

    data = df[available_cols].to_dict(orient='records')
    return {"session_id": session_id, "total_rows": len(data), "data": data}


@router.get("/feedback-data/{session_id}")
async def get_feedback_data(session_id: str, db: DBSession = Depends(get_db)):
    """获取 feedback 数据（从 SQLite）"""
    actions = storage.list_actions(db, session_id, include_deleted=False)
    return {"session_id": session_id, "total_actions": len(actions), "actions": actions}


@router.get("/action-window/{session_id}/{action_index}")
async def get_action_window(session_id: str, action_index: int, db: DBSession = Depends(get_db)):
    """获取单个动作的 IMU 窗口数据（用于样本级可视化）"""
    actions = storage.list_actions(db, session_id)
    action = next((a for a in actions if a["action_index"] == action_index), None)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    csv_content = storage.load_csv(session_id, "raw.csv")
    if not csv_content:
        raise HTTPException(status_code=404, detail="Raw CSV not found")

    df = pd.read_csv(StringIO(csv_content))

    # 用 time 列截取窗口
    time_col = "time" if "time" in df.columns else "seconds_elapsed"
    t_start = action["t_start"]
    t_end = action["t_end"]
    window = df[(df[time_col] >= t_start) & (df[time_col] <= t_end)]

    cols = ['userAccelX', 'userAccelY', 'userAccelZ',
            'rotationRateX', 'rotationRateY', 'rotationRateZ']
    available_cols = [time_col] + [c for c in cols if c in window.columns]

    if all(c in window.columns for c in ['userAccelX', 'userAccelY', 'userAccelZ']):
        window = window.copy()
        window['accMag'] = (window['userAccelX']**2 + window['userAccelY']**2 + window['userAccelZ']**2)**0.5
        available_cols.append('accMag')

    data = window[available_cols].to_dict(orient='records')
    return {
        "session_id": session_id,
        "action_index": action_index,
        "action": action,
        "total_rows": len(data),
        "data": data,
    }
