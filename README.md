# Smart Document Assistant (AI RAG App)

A practical and efficient application that lets you chat directly with your documents. Instead of manually searching through dozens of pages, you upload your files and ask the AI whatever you need.

The project is built with a Multi-Tenant architecture, ensuring each user's data remains private—you can only access and search through the files you uploaded yourself.

---

## What It Can Do

* **Personal Accounts:** Secure registration and login keep your data entirely private.
* **Multiple File Formats:** Supports PDF, Word documents (.docx), plain text (.txt), and direct text pasting.
* **OCR for Scanned Documents:** Utilizes EasyOCR to extract text from scanned PDFs or image-based documents.
* **Document Management:** View all uploaded files in the sidebar and delete any document with a single click.
* **Conversational Memory & Clear Chat:** Remembers the context of previous messages for follow-up questions. Use the Clear Chat button whenever you want a fresh topic.

---

## Tech Stack

* **Frontend:** Streamlit
* **Backend API:** FastAPI (Python)
* **AI & LLM Orchestration:** LangChain + Groq (llama-3.1-8b-instant)
* **Vector Store:** ChromaDB with HuggingFace Embeddings (all-MiniLM-L6-v2)
* **User Database & Security:** SQLite with JWT Authentication

---

## How to Run It Locally

### 1. Clone the repository
`git clone https://github.com/AlexandrosZlatos/YOUR_REPOSITORY.git`  
`cd YOUR_REPOSITORY`

### 2. Set up the environment
`python -m venv .venv`  
`source .venv/bin/activate` (On Mac/Linux)  
`.venv\Scripts\activate` (On Windows)  

`pip install -r requirements.txt`

### 3. Add your API Key
Create a `.env` file in the root directory and add your Groq API key:  
`GROQ_API_KEY=your_actual_api_key_here`

### 4. Launch the application

Open two separate terminal windows:

* **In the 1st terminal (Backend API):**  
  `uvicorn main:app --reload`

* **In the 2nd terminal (Frontend Interface):**  
  `streamlit run streamlit_app.py`

Open your browser and navigate to `http://localhost:8501` to use the application.

## ⚠️ Known Issues & Upcoming Improvements

* **Authentication Endpoint Fallback:** 
  The Streamlit frontend currently uses a two-step fallback mechanism (Form Data $\rightarrow$ JSON) during user login. This is a temporary measure to handle an HTTP 422 schema edge-case with FastAPI.
* **Planned Fix:** 
  Standardizing the API authentication payload to a single unified schema in the upcoming refactor to optimize login performance and response times.