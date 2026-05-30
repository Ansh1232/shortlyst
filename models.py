from database import Base
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Float

class Job(Base):
    __tablename__ = "jobs"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    jd_filepath = Column(String(500), nullable=True)
    session_id  = Column(String(100), nullable=True, index=True)

class Candidate(Base):
    __tablename__ = "candidates"

    id             = Column(Integer, primary_key=True, index=True)
    job_id         = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    name           = Column(String(255), nullable=False)
    file_path      = Column(String(500), nullable=True)
    match_score    = Column(Float, default=0)
    rank           = Column(Integer, default=0)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
