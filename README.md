# Shortlyst

**Notice to Evaluator:** This project utilizes a decoupled client-server architecture for deployment optimization. 

## 1. Project Links
* **Live Application URL:** https://shortlyst.netlify.app/
* **Frontend Repository:** https://github.com/Ansh1232/shortlyst-frontend
* **Backend Repository(Current Repository):** https://github.com/Ansh1232/shortlyst

**Deployment Note:** The backend API is hosted on Render (https://shortlyst-api.onrender.com). If the initial resume analysis experiences a slight delay, the server is waking up from a cold start.Subsequent requests will process instantly.

---

## 2. Setup Instructions (Local Development)

### Frontend Setup (React / Vite)
1. Clone the frontend repository:
   git clone https://github.com/Ansh1232/shortlyst-frontend.git
   cd shortlyst-frontend
2. Install dependencies:
   npm install
3. Create a .env file in the root directory:
   VITE_API_BASE_URL=http://localhost:8000
4. Start the development server:
   npm run dev

### Backend Setup (FastAPI)
1. Clone the backend repository:
   git clone https://github.com/Ansh1232/shortlyst.git
   cd shortlyst
2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate  # (Use venv\Scripts\activate on Windows)
3. Install dependencies:
   pip install -r requirements.txt
4. Create a .env file in the root directory:
   DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>
   GEMINI_API_KEY=<your_gemini_api_key>
5. Start the server:
   uvicorn main:app --reload

---

## 3. Brief Documentation

### Architecture Overview
The application follows a modern decoupled architecture to ensure scalability and separation of concerns:
* **Frontend:** A Single Page Application built with React.js, and TailwindCSS. It is hosted on Netlify.
* **Backend:** A RESTful API built with Python and FastAPI, handling asynchronous file uploads, data parsing, and AI model communication. It is hosted on Render.
* **Database:** A cloud-hosted relational MySQL database managed via Aiven. It securely stores job descriptions, candidate metadata, parsed skills, and historical screening sessions.
* **AI Engine:** Integration with Google Generative AI (Gemini) for natural language processing, semantic extraction, and contextual scoring of unstructured resume data.

### Approach Used for Scoring Candidates
The scoring mechanism evaluates candidates contextually using Large Language Models rather than relying on rigid keyword matching:
1. **Text Extraction:** The backend parses uploaded resume files (PDF/DOCX) and the provided Job Description (JD) to extract raw text content.
2. **Semantic Analysis:** The raw text is passed to the Gemini AI model via a strictly engineered prompt, instructing the model to evaluate the data as a technical recruiter.
3. **Evaluation Criteria:** The AI evaluates the candidate based on:
   * **Matched Skills:** Contextual overlap between the candidate's stated experience and the JD requirements.
   * **Critical Missing Skills:** Core requirements stated in the JD that are entirely absent from the resume.
   * **Experience Alignment:** The overall relevance of the candidate's past roles to the open position.
4. **Score Generation:** The AI returns a structured JSON response containing a calculated match score (0-100) and specific arrays of found/missing skills. The backend logs these metrics, ranks the candidates in descending order, and serves the finalized list to the frontend dashboard.

### Assumptions
* **File Formats:** Uploaded resumes are in standard .pdf or .docx formats and contain selectable text (not flattened or scanned images requiring OCR).
* **Language:** Resumes and job descriptions provided to the system are written in English.
* **JD Quality:** The provided job description contains sufficient specific criteria (skills, experience levels, responsibilities) for the AI to generate an accurate baseline for comparison.
* **Stateless Processing:** Uploaded resume files are processed in-memory. Extracted data and scores are saved to the database, but the physical files are not permanently stored on the server to ensure candidate data privacy.
