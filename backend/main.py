"""
FastAPI 主入口
Tennis Coach API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db.database import init_db
from routers import sessions, projects, training, visualization

app = FastAPI(
    title="Tennis Coach API",
    description="网球教练 App 配套 API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时创建数据库表
@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(training.router, prefix="/api/training", tags=["Training"])
app.include_router(visualization.router, prefix="/api/viz", tags=["Visualization"])


@app.get("/")
async def root():
    return {"message": "Tennis Coach API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
