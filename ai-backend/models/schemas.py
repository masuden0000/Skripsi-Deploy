from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    skema: str
    tahun: str


class ProjectStatus(BaseModel):
    id: str
    skema: str
    tahun: str
    source_file: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    result_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectResponse(BaseModel):
    data: ProjectStatus
    message: Optional[str] = None


class ProjectListResponse(BaseModel):
    data: list[ProjectStatus]