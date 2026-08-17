from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models import ProjectRole

# Project member schemas


class ProjectMemberBase(BaseModel):
    user_id: int
    project_id: int
    role: ProjectRole = ProjectRole.VIEWER


class ProjectMemberCreate(ProjectMemberBase):
    pass


class ProjectMemberResponse(ProjectMemberBase):
    model_config = ConfigDict(from_attributes=True)


# Document schemas


class DocumentBase(BaseModel):
    file_name: str
    file_size: int


class DocumentCreate(DocumentBase):
    s3_key: str


class DocumentResponse(DocumentBase):
    id: int
    file_name: str
    file_size: int
    s3_key: str
    project_id: int

    model_config = ConfigDict(from_attributes=True)


# Project schemas


class ProjectBase(BaseModel):
    name: str
    description: Optional[str]


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    documents: list[DocumentResponse] = []

    model_config = ConfigDict(from_attributes=True)
