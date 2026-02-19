"""
Session 管理路由
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from typing import Optional
import uuid
import pandas as pd
from io import StringIO

from sqlalchemy.orm import Session as DBSession
from db.database import get_db
from services.csv_parser import parse_raw_csv, parse_feedback_csv, validate_csv_format
from services import storage

router = APIRouter()

# feedback CSV 中 40 维特征的列名
FEATURE_COLS = [
    'mean_accX', 'std_accX', 'max_accX', 'min_accX', 'simpson_accX',
    'mean_accY', 'std_accY', 'max_accY', 'min_accY', 'simpson_accY',
    'mean_accZ', 'std_accZ', 'max_accZ', 'min_accZ', 'simpson_accZ',
    'mean_accMag', 'std_accMag', 'max_accMag', 'min_accMag', 'simpson_accMag',
    'mean_gyroX', 'std_gyroX', 'max_gyroX', 'min_gyroX', 'simpson_gyroX',
    'mean_gyroY', 'std_gyroY', 'max_gyroY', 'min_gyroY', 'simpson_gyroY',
    'mean_gyroZ', 'std_gyroZ', 'max_gyroZ', 'min_gyroZ', 'simpson_gyroZ',
    'mean_gyroMag', 'std_gyroMag', 'max_gyroMag', 'min_gyroMag', 'simpson_gyroMag',
]


def _extract_features_from_row(row: pd.Series) -> Optional[list]:
    """从 feedback CSV 的一行提取 40 维特征"""
    available = [c for c in FEATURE_COLS if c in row.index]
    if len(available) < 5:
        return None
    return [float(row[c]) if pd.notna(row[c]) else 0.0 for c in available]


@router.post("/upload")
async def upload_session(
    raw_csv: UploadFile = File(...),
    feedback_csv: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    session_name: Optional[str] = Form(None),
    db: DBSession = Depends(get_db),
):
    """上传 session 的两个 CSV 文件"""
    try:
        raw_content = (await raw_csv.read()).decode('utf-8')
        feedback_content = (await feedback_csv.read()).decode('utf-8')

        raw_df = parse_raw_csv(raw_content)
        feedback_df = parse_feedback_csv(feedback_content)

        is_valid, error_msg = validate_csv_format(raw_df, 'raw')
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Raw CSV 格式错误: {error_msg}")

        is_valid, error_msg = validate_csv_format(feedback_df, 'feedback')
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Feedback CSV 格式错误: {error_msg}")

        session_id = str(raw_df['session_id'].iloc[0]) if len(raw_df) > 0 else str(uuid.uuid4())

        good_count = len(feedback_df[feedback_df['manual_quality'] == 'good'])
        bad_count = len(feedback_df[feedback_df['manual_quality'] == 'bad'])
        unlabeled_count = len(feedback_df) - good_count - bad_count

        # 保存 CSV 文件到文件系统
        storage.save_csv(session_id, "raw.csv", raw_content)
        storage.save_csv(session_id, "feedback.csv", feedback_content)

        # 保存 session 元数据到 SQLite
        session_data = {
            "name": session_name or f"Session {session_id[:8]}",
            "project_id": project_id if project_id else None,
            "action_count": len(feedback_df),
            "raw_rows": len(raw_df),
            "good_count": good_count,
            "bad_count": bad_count,
            "unlabeled_count": unlabeled_count,
            "session_type": str(raw_df['session_type'].iloc[0]) if 'session_type' in raw_df.columns else "",
        }
        storage.save_session(db, session_id, session_data)

        # 解析 feedback 行 → actions 表
        actions_data = []
        for _, row in feedback_df.iterrows():
            actions_data.append({
                "action_index": int(row["action_index"]),
                "t_peak": float(row["t_peak"]),
                "t_start": float(row["t_start"]),
                "t_end": float(row["t_end"]),
                "ml_classification": str(row.get("ml_classification", "")),
                "ml_quality": str(row.get("ml_quality", "")),
                "manual_quality": str(row.get("manual_quality", "unlabeled")),
                "features": _extract_features_from_row(row),
            })
        storage.save_actions(db, session_id, actions_data)

        return {
            "status": "success",
            "id": session_id,
            "name": session_data["name"],
            "action_count": len(feedback_df),
            "good_count": good_count,
            "bad_count": bad_count,
            "unlabeled_count": unlabeled_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_sessions(project_id: Optional[str] = None, db: DBSession = Depends(get_db)):
    sessions = storage.list_sessions(db, project_id)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/{session_id}")
async def get_session(session_id: str, db: DBSession = Depends(get_db)):
    session = storage.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    storage.delete_session(db, session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/actions")
async def get_session_actions(session_id: str, include_deleted: bool = False, db: DBSession = Depends(get_db)):
    """获取 session 的所有动作"""
    actions = storage.list_actions(db, session_id, include_deleted=include_deleted)
    return {"session_id": session_id, "total": len(actions), "actions": actions}


@router.post("/{session_id}/actions/delete")
async def soft_delete_actions(session_id: str, action_ids: list[int], db: DBSession = Depends(get_db)):
    """软删除动作"""
    storage.soft_delete_actions(db, action_ids)
    storage.update_session_counts(db, session_id)
    session = storage.get_session(db, session_id)
    return {"status": "deleted", "remaining": session}


@router.post("/{session_id}/actions/restore")
async def restore_actions(session_id: str, action_ids: list[int], db: DBSession = Depends(get_db)):
    """恢复已删除的动作"""
    storage.restore_actions(db, action_ids)
    storage.update_session_counts(db, session_id)
    session = storage.get_session(db, session_id)
    return {"status": "restored", "remaining": session}


@router.put("/{session_id}/actions/{action_id}")
async def update_action(session_id: str, action_id: int, updates: dict, db: DBSession = Depends(get_db)):
    """更新单个动作（比如修改 manual_quality）"""
    allowed_fields = {"manual_quality", "is_deleted"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    storage.update_action(db, action_id, safe_updates)
    storage.update_session_counts(db, session_id)
    return {"status": "updated"}
