"""
模型训练路由
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid

from sqlalchemy.orm import Session as DBSession
from db.database import get_db
from services import storage
from services.model_trainer import run_training

router = APIRouter()


class TrainingRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    project_id: str = ""
    session_ids: list[str]
    model_type: str = "svm"
    svm_c: float = 1.0
    svm_kernel: str = "rbf"
    max_depth: Optional[int] = None
    n_estimators: int = 100


@router.post("/start")
async def start_training(body: TrainingRequest, db: DBSession = Depends(get_db)):
    if not body.session_ids:
        raise HTTPException(status_code=400, detail="至少选择一个 session")

    run_id = str(uuid.uuid4())[:8]

    try:
        result = run_training(
            db=db,
            run_id=run_id,
            session_ids=body.session_ids,
            model_type=body.model_type,
            svm_c=body.svm_c,
            svm_kernel=body.svm_kernel,
            max_depth=body.max_depth,
            n_estimators=body.n_estimators,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def list_training_runs(db: DBSession = Depends(get_db)):
    runs = storage.list_training_runs(db)
    return {"runs": runs}


@router.get("/status/{run_id}")
async def get_training_status(run_id: str, db: DBSession = Depends(get_db)):
    run = storage.get_training_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Training run not found")
    return run


@router.get("/download/{run_id}")
async def download_model(run_id: str, fmt: str = "auto"):
    """下载模型文件。fmt: auto/mlmodel/pkl"""
    # 优先 mlmodel，其次 pkl
    if fmt == "mlmodel":
        exts = [".mlmodel"]
    elif fmt == "pkl":
        exts = [".pkl"]
    else:
        exts = [".mlmodel", ".pkl"]

    for ext in exts:
        model_path = storage.get_model_path(run_id, ext=ext)
        if model_path.exists():
            return FileResponse(
                path=str(model_path),
                filename=f"tennis_model_{run_id}{ext}",
                media_type="application/octet-stream",
            )
    raise HTTPException(status_code=404, detail="Model file not found")
