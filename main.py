from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from app.services.rag_engine import RAGEngine
from app.services.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services.db import init_db, add_user, get_user_hash

app = FastAPI(title="AI RAG SaaS API")
rag_engine = RAGEngine()

init_db()

class UserAuthInput(BaseModel):
    username: str
    password: str

class DocumentInput(BaseModel):
    content: str
    document_id: str | None = None

class ChatInput(BaseModel):
    question: str
    history: list[dict] | None = []

@app.post("/api/v1/register")
def register(user: UserAuthInput):
    hashed_pwd = hash_password(user.password)
    success = add_user(user.username, hashed_pwd)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists.")
    return {"status": "success", "message": "User registered successfully."}

@app.post("/api/v1/login")
def login(user: UserAuthInput):
    hashed_pwd = get_user_hash(user.username)
    if not hashed_pwd or not verify_password(user.password, hashed_pwd):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    token = create_access_token({"sub": user.username})
    return {"status": "success", "token": token, "username": user.username}

@app.get("/api/v1/documents")
def list_documents(current_user: str = Depends(get_current_user)):
    try:
        docs = rag_engine.get_user_documents(user_id=current_user)
        return {"status": "success", "data": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/documents/{document_id}")
def delete_document(document_id: str, current_user: str = Depends(get_current_user)):
    try:
        deleted = rag_engine.delete_document(user_id=current_user, document_id=document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found or access denied.")
        return {"status": "success", "message": f"Document '{document_id}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/documents")
def store_document(payload: DocumentInput, current_user: str = Depends(get_current_user)):
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    try:
        result = rag_engine.process_and_store(payload.content, user_id=current_user, document_id=payload.document_id)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/documents/upload-file")
async def upload_file(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    filename = file.filename.lower()
    contents = await file.read()
    
    try:
        if filename.endswith(".pdf"):
            result = rag_engine.process_pdf_file(contents, file.filename, user_id=current_user)
        elif filename.endswith(".docx"):
            result = rag_engine.process_docx_file(contents, file.filename, user_id=current_user)
        elif filename.endswith(".txt"):
            result = rag_engine.process_txt_file(contents, file.filename, user_id=current_user)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use PDF, DOCX, or TXT.")

        return {"status": "success", "message": f"File '{file.filename}' processed successfully.", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
def rag_chat(payload: ChatInput, current_user: str = Depends(get_current_user)):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        response = rag_engine.generate_answer(payload.question, user_id=current_user, history=payload.history)
        return {"status": "success", "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))