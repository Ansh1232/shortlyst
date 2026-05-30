from pydantic import BaseModel
from typing import List, Optional

class JobCreate(BaseModel):
    title: str
    description: Optional[str] = None
    jd_filepath: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class JobResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    jd_filepath: Optional[str] = None

    class Config:
        from_attributes = True

class CandidateResponse(BaseModel):
    id: int
    job_id: int
    name: str
    file_path: Optional[str]
    match_score: float
    rank: int
    matched_skills: List[str]
    missing_skills: List[str]

    class Config:
        from_attributes = True

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
