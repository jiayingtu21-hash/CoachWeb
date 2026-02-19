"""
存储服务 - SQLite + 文件系统
结构化数据用 SQLite，CSV/模型文件用文件系统
"""
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from config import settings
from db.models import Project, Session, Action, TrainingRun


def _ensure_file_dirs():
    """确保文件存储目录存在"""
    base = Path(settings.data_dir)
    (base / "csv_files").mkdir(parents=True, exist_ok=True)
    (base / "models").mkdir(parents=True, exist_ok=True)


# ---- Projects ----

def list_projects(db: DBSession) -> list[dict]:
    projects = db.query(Project).order_by(Project.created_at).all()
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at.isoformat() if p.created_at else "",
            "session_count": len(p.sessions),
        })
    return result


def get_project(db: DBSession, project_id: str) -> Optional[dict]:
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        return None
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "session_count": len(p.sessions),
    }


def create_project(db: DBSession, project_id: str, name: str, description: str = "") -> dict:
    p = Project(id=project_id, name=name, description=description)
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "created_at": p.created_at.isoformat() if p.created_at else "",
    }


def delete_project(db: DBSession, project_id: str) -> bool:
    p = db.query(Project).filter(Project.id == project_id).first()
    if p:
        db.delete(p)
        db.commit()
        return True
    return False


# ---- Sessions ----

def list_sessions(db: DBSession, project_id: Optional[str] = None) -> list[dict]:
    query = db.query(Session)
    if project_id:
        query = query.filter(Session.project_id == project_id)
    sessions = query.order_by(Session.created_at).all()
    return [_session_to_dict(s) for s in sessions]


def get_session(db: DBSession, session_id: str) -> Optional[dict]:
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        return None
    return _session_to_dict(s)


def save_session(db: DBSession, session_id: str, data: dict):
    """创建或更新 session"""
    s = db.query(Session).filter(Session.id == session_id).first()
    if s:
        for key, val in data.items():
            if key != "id" and hasattr(s, key):
                setattr(s, key, val)
    else:
        s = Session(
            id=session_id,
            name=data.get("name", f"Session {session_id[:8]}"),
            project_id=data.get("project_id") or None,
            session_type=data.get("session_type", ""),
            raw_rows=data.get("raw_rows", 0),
            action_count=data.get("action_count", 0),
            good_count=data.get("good_count", 0),
            bad_count=data.get("bad_count", 0),
            unlabeled_count=data.get("unlabeled_count", 0),
        )
        db.add(s)
    db.commit()


def delete_session(db: DBSession, session_id: str) -> bool:
    s = db.query(Session).filter(Session.id == session_id).first()
    if s:
        db.delete(s)
        db.commit()
    # 删除关联 CSV 文件
    csv_dir = Path(settings.data_dir) / "csv_files" / session_id
    if csv_dir.exists():
        shutil.rmtree(csv_dir)
    return True


def _session_to_dict(s: Session) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "project_id": s.project_id or "",
        "session_type": s.session_type or "",
        "raw_rows": s.raw_rows,
        "action_count": s.action_count,
        "good_count": s.good_count,
        "bad_count": s.bad_count,
        "unlabeled_count": s.unlabeled_count,
        "created_at": s.created_at.isoformat() if s.created_at else "",
    }


# ---- Actions ----

def save_actions(db: DBSession, session_id: str, actions_data: list[dict]):
    """批量保存动作数据（从 feedback CSV 解析）"""
    # 先删除该 session 的旧 actions
    db.query(Action).filter(Action.session_id == session_id).delete()

    for a in actions_data:
        action = Action(
            session_id=session_id,
            action_index=a["action_index"],
            t_peak=a["t_peak"],
            t_start=a["t_start"],
            t_end=a["t_end"],
            ml_classification=a.get("ml_classification", ""),
            ml_quality=a.get("ml_quality", ""),
            manual_quality=a.get("manual_quality", "unlabeled"),
            features=a.get("features"),
            is_deleted=False,
        )
        db.add(action)
    db.commit()


def list_actions(db: DBSession, session_id: str, include_deleted: bool = False) -> list[dict]:
    query = db.query(Action).filter(Action.session_id == session_id)
    if not include_deleted:
        query = query.filter(Action.is_deleted == False)
    actions = query.order_by(Action.action_index).all()
    return [_action_to_dict(a) for a in actions]


def update_action(db: DBSession, action_id: int, updates: dict):
    a = db.query(Action).filter(Action.id == action_id).first()
    if a:
        for key, val in updates.items():
            if hasattr(a, key):
                setattr(a, key, val)
        db.commit()


def soft_delete_actions(db: DBSession, action_ids: list[int]):
    db.query(Action).filter(Action.id.in_(action_ids)).update(
        {"is_deleted": True}, synchronize_session="fetch"
    )
    db.commit()


def restore_actions(db: DBSession, action_ids: list[int]):
    db.query(Action).filter(Action.id.in_(action_ids)).update(
        {"is_deleted": False}, synchronize_session="fetch"
    )
    db.commit()


def get_training_actions(db: DBSession, session_ids: list[str]) -> list[dict]:
    """获取训练用的 actions（排除 deleted 和 unlabeled）"""
    actions = (
        db.query(Action)
        .filter(
            Action.session_id.in_(session_ids),
            Action.is_deleted == False,
            Action.manual_quality.in_(["good", "bad"]),
        )
        .order_by(Action.session_id, Action.action_index)
        .all()
    )
    return [_action_to_dict(a) for a in actions]


def update_session_counts(db: DBSession, session_id: str):
    """重新计算 session 的 good/bad/unlabeled 数量"""
    s = db.query(Session).filter(Session.id == session_id).first()
    if not s:
        return
    active_actions = db.query(Action).filter(
        Action.session_id == session_id,
        Action.is_deleted == False,
    ).all()
    s.action_count = len(active_actions)
    s.good_count = sum(1 for a in active_actions if a.manual_quality == "good")
    s.bad_count = sum(1 for a in active_actions if a.manual_quality == "bad")
    s.unlabeled_count = sum(1 for a in active_actions if a.manual_quality not in ("good", "bad"))
    db.commit()


def _action_to_dict(a: Action) -> dict:
    return {
        "id": a.id,
        "session_id": a.session_id,
        "action_index": a.action_index,
        "t_peak": a.t_peak,
        "t_start": a.t_start,
        "t_end": a.t_end,
        "ml_classification": a.ml_classification or "",
        "ml_quality": a.ml_quality or "",
        "manual_quality": a.manual_quality or "unlabeled",
        "features": a.features,
        "is_deleted": a.is_deleted,
    }


# ---- Training Runs ----

def save_training_run(db: DBSession, run_id: str, data: dict):
    run = TrainingRun(
        id=run_id,
        project_id=data.get("project_id") or None,
        model_type=data["model_type"],
        hyperparameters=data.get("hyperparams", {}),
        session_ids=data.get("session_ids", []),
        sample_count=data.get("sample_count", 0),
        good_count=data.get("good_count", 0),
        bad_count=data.get("bad_count", 0),
        feature_count=data.get("feature_count", 40),
        accuracy=data.get("accuracy"),
        precision=data.get("precision"),
        recall=data.get("recall"),
        f1_score=data.get("f1_score"),
        cv_mean=data.get("cv_mean"),
        cv_std=data.get("cv_std"),
        confusion_matrix=data.get("confusion_matrix"),
        labels=data.get("labels"),
        status=data.get("status", "completed"),
        coreml_exported=data.get("coreml_exported", False),
        completed_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()


def get_training_run(db: DBSession, run_id: str) -> Optional[dict]:
    r = db.query(TrainingRun).filter(TrainingRun.id == run_id).first()
    if not r:
        return None
    return _run_to_dict(r)


def list_training_runs(db: DBSession) -> list[dict]:
    runs = db.query(TrainingRun).order_by(TrainingRun.created_at).all()
    return [_run_to_dict(r) for r in runs]


def _run_to_dict(r: TrainingRun) -> dict:
    return {
        "run_id": r.id,
        "project_id": r.project_id or "",
        "status": r.status,
        "model_type": r.model_type,
        "session_ids": r.session_ids or [],
        "sample_count": r.sample_count,
        "good_count": r.good_count,
        "bad_count": r.bad_count,
        "feature_count": r.feature_count,
        "accuracy": r.accuracy,
        "precision": r.precision,
        "recall": r.recall,
        "f1_score": r.f1_score,
        "cv_mean": r.cv_mean,
        "cv_std": r.cv_std,
        "confusion_matrix": r.confusion_matrix,
        "labels": r.labels,
        "coreml_exported": r.coreml_exported,
        "hyperparams": r.hyperparameters or {},
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


# ---- CSV 文件操作（仍用文件系统）----

def save_csv(session_id: str, filename: str, content: str):
    _ensure_file_dirs()
    csv_dir = Path(settings.data_dir) / "csv_files" / session_id
    csv_dir.mkdir(parents=True, exist_ok=True)
    (csv_dir / filename).write_text(content, encoding="utf-8")


def load_csv(session_id: str, filename: str) -> Optional[str]:
    path = Path(settings.data_dir) / "csv_files" / session_id / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


# ---- 模型文件操作（仍用文件系统）----

def get_model_path(run_id: str, ext: str = ".mlmodel") -> Path:
    _ensure_file_dirs()
    return Path(settings.data_dir) / "models" / f"{run_id}{ext}"


# ---- Chat Messages ----

from db.models import ChatMessage


def save_chat_message(db: DBSession, conversation_id: str, role: str, content: str,
                      tool_calls: Optional[list] = None) -> dict:
    msg = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return _chat_message_to_dict(msg)


def list_chat_messages(db: DBSession, conversation_id: str) -> list[dict]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [_chat_message_to_dict(m) for m in messages]


def list_conversations(db: DBSession, limit: int = 20) -> list[dict]:
    from sqlalchemy import func
    results = (
        db.query(
            ChatMessage.conversation_id,
            func.max(ChatMessage.created_at).label("last_active"),
            func.count(ChatMessage.id).label("message_count"),
        )
        .group_by(ChatMessage.conversation_id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "conversation_id": r.conversation_id,
            "last_active": r.last_active.isoformat() if r.last_active else "",
            "message_count": r.message_count,
        }
        for r in results
    ]


def _chat_message_to_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "tool_calls": m.tool_calls,
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }
