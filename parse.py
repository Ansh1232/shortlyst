import pdfplumber
from docx import Document
import os

def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    elif ext == ".docx":
        return _extract_from_docx(file_path)
    elif ext == ".doc":
        raise ValueError("DOC format not supported. Please upload PDF or DOCX.")
    else:
        raise ValueError(f"Unsupported format: {ext}")

def _extract_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def _extract_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(
        para.text for para in doc.paragraphs if para.text.strip()
    )