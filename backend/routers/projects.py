"""
Project 管理路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid

from sqlalchemy.orm import Session as DBSession
from db.database import get_db
from services import storage

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


@router.get("/list")
async def list_projects(db: DBSession = Depends(get_db)):
    projects = storage.list_projects(db)
    return {"projects": projects}


@router.post("/create")
async def create_project(body: ProjectCreate, db: DBSession = Depends(get_db)):
    project_id = str(uuid.uuid4())[:8]
    proj = storage.create_project(db, project_id, body.name, body.description)
    return {"status": "success", "project": proj}


@router.get("/{project_id}")
async def get_project(project_id: str, db: DBSession = Depends(get_db)):
    proj = storage.get_project(db, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    sessions = storage.list_sessions(db, project_id)
    proj["sessions"] = sessions
    return proj


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: DBSession = Depends(get_db)):
    storage.delete_project(db, project_id)
    return {"status": "deleted"}
