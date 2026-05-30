"""
Shared Project Schema - Source of Truth
Dipakai oleh: Express Backend, FastAPI AI Backend
"""
from enum import Enum
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectStatus(str, Enum):
    PENDING_UPLOAD = "pending_upload"
    PENDING = "pending"
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectCreateRequest(BaseModel):
    skema: str
    tahun: str


class Project(BaseModel):
    id: str
    skema: str
    tahun: str
    source_file: Optional[str] = None
    source_url: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PENDING
    error_message: Optional[str] = None
    result_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApiResponse(BaseModel):
    success: bool
    data: Optional[Project] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ProjectListResponse(BaseModel):
    success: bool
    data: list[Project]
    error: Optional[str] = None


class ProjectDetailResponse(BaseModel):
    success: bool
    data: Optional[Project] = None
    error: Optional[str] = None