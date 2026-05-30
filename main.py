import os
import uuid
import csv
import io
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas, database, parse, checkScore
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Screening API")

# CORS — sabse pehle, routes se pehle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def recalculate_ranks(job_id: int, db: Session):
    candidates = (
        db.query(models.Candidate)
        .filter(models.Candidate.job_id == job_id)
        .order_by(models.Candidate.match_score.desc())
        .all()
    )
    for i, c in enumerate(candidates, start=1):
        c.rank = i
    db.commit()


@app.get("/api/jobs", response_model=List[schemas.JobResponse])
def list_jobs(session_id: str = Query(default=""), db: Session = Depends(get_db)):
    q = db.query(models.Job).order_by(models.Job.id.desc())
    if session_id.strip():
        q = q.filter(models.Job.session_id == session_id.strip())
    return q.all()


@app.get("/api/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.post("/api/jobs", response_model=schemas.JobResponse, status_code=201)
async def create_job(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not description and not jd_file:
        raise HTTPException(status_code=400, detail="Must provide either text description or JD file.")
    
    extracted_desc = ""
    file_path = None
    
    if jd_file:
        ext = os.path.splitext(jd_file.filename)[1].lower()
        if ext not in (".pdf", ".docx"):
            raise HTTPException(status_code=400, detail="JD File must be .pdf or .docx")
            
        unique_name = f"jd_{uuid.uuid4().hex}{ext}"
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        
        contents = await jd_file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            
        try:
            extracted_desc = parse.extract_text(file_path)
        except Exception as e:
            os.remove(file_path)
            raise HTTPException(status_code=422, detail=f"Could not read JD document: {e}")

    final_desc = description.strip() if description else extracted_desc.strip()
    if not final_desc:
        raise HTTPException(status_code=400, detail="Parsed JD was empty.")

    db_job = models.Job(
        title=title.strip(),
        description=final_desc,
        jd_filepath=file_path,
        session_id=session_id.strip() if session_id else None
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@app.patch("/api/jobs/{job_id}", response_model=schemas.JobResponse)
def update_job(job_id: int, payload: schemas.JobUpdate, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    should_rescore = False

    if payload.title is not None:
        clean_title = payload.title.strip()
        if not clean_title:
            raise HTTPException(status_code=400, detail="Title cannot be empty.")
        job.title = clean_title

    if payload.description is not None:
        clean_description = payload.description.strip()
        if not clean_description:
            raise HTTPException(status_code=400, detail="Description cannot be empty.")
        if clean_description != job.description:
            job.description = clean_description
            should_rescore = True

    if should_rescore:
        candidates = db.query(models.Candidate).filter(models.Candidate.job_id == job_id).all()
        for candidate in candidates:
            if not candidate.file_path:
                continue
            try:
                resume_text = parse.extract_text(candidate.file_path)
                score, matched, missing = checkScore.calculate_score(job.description, resume_text)
            except Exception:
                score, matched, missing = 0, [], []

            candidate.match_score = score
            candidate.matched_skills = matched
            candidate.missing_skills = missing

    db.commit()
    if should_rescore:
        recalculate_ranks(job_id, db)
    db.refresh(job)
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidates = db.query(models.Candidate).filter(models.Candidate.job_id == job_id).all()
    for candidate in candidates:
        if candidate.file_path and os.path.exists(candidate.file_path):
            os.remove(candidate.file_path)
        db.delete(candidate)

    if job.jd_filepath and os.path.exists(job.jd_filepath):
        os.remove(job.jd_filepath)

    db.delete(job)
    db.commit()


@app.post("/api/jobs/{job_id}/candidates", response_model=schemas.CandidateResponse, status_code=201)
async def upload_candidate(
    job_id: int,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    allowed = (".pdf", ".docx")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Only PDF and DOCX allowed. Got: {ext}")

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path   = os.path.join(UPLOAD_DIR, unique_name)
    contents    = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        resume_text = parse.extract_text(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Could not read file: {e}")

    score, matched, missing = checkScore.calculate_score(job.description, resume_text)

    candidate = models.Candidate(
        job_id         = job_id,
        name           = name.strip(),
        file_path      = file_path,
        match_score    = score,
        matched_skills = matched,
        missing_skills = missing,
        rank           = 0,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    recalculate_ranks(job_id, db)
    db.refresh(candidate)

    return candidate


@app.get("/api/jobs/{job_id}/candidates", response_model=List[schemas.CandidateResponse])
def get_candidates(
    job_id: int,
    search: str = Query(default="", description="Filter by name"),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    query = db.query(models.Candidate).filter(models.Candidate.job_id == job_id)
    if search.strip():
        query = query.filter(models.Candidate.name.ilike(f"%{search.strip()}%"))

    candidates = query.order_by(models.Candidate.rank.asc()).all()
    needs_rank_refresh = False

    for candidate in candidates:
        has_no_skill_breakdown = not (candidate.matched_skills or candidate.missing_skills)
        if candidate.match_score == 0 and has_no_skill_breakdown and candidate.file_path:
            try:
                resume_text = parse.extract_text(candidate.file_path)
                score, matched, missing = checkScore.fallback_score(job.description or "", resume_text)
            except Exception:
                continue

            candidate.match_score = score
            candidate.matched_skills = matched
            candidate.missing_skills = missing
            needs_rank_refresh = True

    if needs_rank_refresh:
        db.commit()
        recalculate_ranks(job_id, db)
        candidates = query.order_by(models.Candidate.rank.asc()).all()

    return candidates


@app.get("/api/jobs/{job_id}/candidates/{candidate_id}", response_model=schemas.CandidateResponse)
def get_candidate(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        models.Candidate.job_id == job_id
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return c


@app.patch("/api/jobs/{job_id}/candidates/{candidate_id}", response_model=schemas.CandidateResponse)
def update_candidate(
    job_id: int,
    candidate_id: int,
    payload: schemas.CandidateUpdate,
    db: Session = Depends(get_db)
):
    c = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        models.Candidate.job_id == job_id
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Name cannot be empty.")
        c.name = clean_name

    db.commit()
    db.refresh(c)
    return c


@app.delete("/api/jobs/{job_id}/candidates/{candidate_id}", status_code=204)
def delete_candidate(job_id: int, candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id,
        models.Candidate.job_id == job_id
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if c.file_path and os.path.exists(c.file_path):
        os.remove(c.file_path)
    db.delete(c)
    db.commit()
    recalculate_ranks(job_id, db)


@app.get("/api/jobs/{job_id}/export/csv")
def export_csv(job_id: int, db: Session = Depends(get_db)):
    candidates = (
        db.query(models.Candidate)
        .filter(models.Candidate.job_id == job_id)
        .order_by(models.Candidate.rank.asc())
        .all()
    )
    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rank", "Name", "Match Score", "Matched Skills", "Missing Skills"])
    for c in candidates:
        writer.writerow([
            c.rank,
            c.name,
            c.match_score,
            ", ".join(c.matched_skills or []),
            ", ".join(c.missing_skills or []),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=candidates_job{job_id}.csv"},
    )
    
