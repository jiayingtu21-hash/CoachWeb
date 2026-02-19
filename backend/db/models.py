"""
SQLAlchemy ORM 模型
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    training_runs = relationship("TrainingRun", back_populates="project", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, nullable=False)
    session_type = Column(String, default="")

    raw_rows = Column(Integer, default=0)
    action_count = Column(Integer, default=0)
    good_count = Column(Integer, default=0)
    bad_count = Column(Integer, default=0)
    unlabeled_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="sessions")
    actions = relationship("Action", back_populates="session", cascade="all, delete-orphan")


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    action_index = Column(Integer, nullable=False)
    t_peak = Column(Float, nullable=False)
    t_start = Column(Float, nullable=False)
    t_end = Column(Float, nullable=False)

    ml_classification = Column(String, default="")
    ml_quality = Column(String, default="")
    manual_quality = Column(String, default="unlabeled")

    # 40 维特征存为 JSON array
    features = Column(JSON, nullable=True)

    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="actions")


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    model_type = Column(String, nullable=False)
    hyperparameters = Column(JSON, default=dict)
    session_ids = Column(JSON, default=list)  # list of session id strings

    sample_count = Column(Integer, default=0)
    good_count = Column(Integer, default=0)
    bad_count = Column(Integer, default=0)
    feature_count = Column(Integer, default=40)

    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    cv_mean = Column(Float)
    cv_std = Column(Float)
    confusion_matrix = Column(JSON)
    labels = Column(JSON)

    status = Column(String, default="pending")  # pending / training / completed / failed
    coreml_exported = Column(Boolean, default=False)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="training_runs")
