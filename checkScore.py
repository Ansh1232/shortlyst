import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SKILL_PATTERNS = [
    ("RAG", r"\brag\b|\bretrieval[-\s]?augmented generation\b"),
    ("React", r"\breact(?:\.js|js)?\b"),
    ("JavaScript", r"\bjavascript\b|\bjs\b"),
    ("TypeScript", r"\btypescript\b|\bts\b"),
    ("HTML", r"\bhtml5?\b"),
    ("CSS", r"\bcss3?\b"),
    ("REST API", r"\brest(?:ful)?\s+api\b|\bapis?\b"),
    ("SQL", r"\bsql\b"),
    ("Python", r"\bpython\b"),
    ("FastAPI", r"\bfastapi\b"),
    ("Node.js", r"\bnode(?:\.js|js)?\b"),
    ("Express", r"\bexpress(?:\.js|js)?\b"),
    ("MongoDB", r"\bmongodb\b"),
    ("MySQL", r"\bmysql\b"),
    ("PostgreSQL", r"\bpostgres(?:ql)?\b"),
    ("Machine Learning", r"\bmachine learning\b|\bml\b"),
    ("LLM", r"\bllm\b|\blarge language model\b"),
    ("Gemini", r"\bgemini\b"),
    ("AWS", r"\baws\b|\bamazon web services\b"),
    ("Docker", r"\bdocker\b"),
    ("Git", r"\bgit\b|\bgithub\b"),
]

def _has_term(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text or "", flags=re.IGNORECASE))

def fallback_score(job_description: str, resume_text: str):
    required = []
    for label, pattern in SKILL_PATTERNS:
        if _has_term(job_description, pattern):
            required.append((label, pattern))

    if not required:
        return 0, [], []

    matched = [label for label, pattern in required if _has_term(resume_text, pattern)]
    missing = [label for label, pattern in required if not _has_term(resume_text, pattern)]
    score = round((len(matched) / len(required)) * 100, 2)

    return score, matched, missing

def calculate_score(job_description: str, resume_text: str):
    if not api_key:
        return fallback_score(job_description, resume_text)
        
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) strictly evaluating a candidate's resume against a job description.
    
    Job Description:
    {job_description}
    
    Candidate Resume:
    {resume_text}
    
    CRITICAL INSTRUCTIONS:
    1. You must ONLY look for skills that are EXPLICITLY written in the Job Description. Do not assume, invent, or add general industry skills (like "Cloud Platforms", "Vector Databases", etc.) unless they are specifically mentioned in the Job Description text.
    2. Evaluate if the candidate has these explicitly mentioned skills.
    3. Generate a match_score from 0 to 100 representing how well the candidate fits.
    4. matched_skills: List ONLY the skills specifically requested in the Job Description that the candidate possesses.
    5. missing_skills: List ONLY the skills specifically requested in the Job Description that the candidate lacks.
    
    You must output ONLY valid JSON in this exact format, with no markdown formatting or other text:
    {{
        "score": 85,
        "matched_skills": ["Skill1", "Skill2"],
        "missing_skills": ["Skill3"]
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        # Clean up response text to parse json
        response_text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(response_text)
        
        score = float(result.get("score", 0))
        matched = result.get("matched_skills", [])
        missing = result.get("missing_skills", [])

        if not matched and not missing:
            return fallback_score(job_description, resume_text)
        
        return score, matched, missing
    except Exception as e:
        return fallback_score(job_description, resume_text)
