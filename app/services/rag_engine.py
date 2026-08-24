import os
import uuid
import io
import fitz  # PyMuPDF
import docx  # python-docx
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq

load_dotenv()

_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['el', 'en'], gpu=False)
    return _ocr_reader

class RAGEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len
        )

        self.vector_store = Chroma(
            collection_name="saas_knowledge_base",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db"
        )

        self.llm = ChatGroq(
            temperature=0.2,
            model_name="openai/gpt-oss-20b",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

    def process_and_store(self, text: str, user_id: str, document_id: str = None):
        """
        Splits text, generates embeddings, and stores them in ChromaDB with user isolation.
        """
        if not document_id:
            preview = text.strip()[:15].replace(" ", "_")
            document_id = f"note_{preview}_{uuid.uuid4().hex[:4]}"

        chunks = self.text_splitter.split_text(text)
        metadatas = [{"document_id": document_id, "user_id": user_id, "chunk_index": i} for i in range(len(chunks))]
        
        self.vector_store.add_texts(
            texts=chunks,
            metadatas=metadatas
        )

        return {
            "document_id": document_id,
            "total_chunks_stored": len(chunks)
        }

    def process_pdf_file(self, file_bytes: bytes, filename: str, user_id: str) -> dict:
        """
        Extracts text using PyMuPDF (fitz), falling back to EasyOCR if image-based/scanned.
        """
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        extracted_text = ""

        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                extracted_text += page_text + "\n"

        if not extracted_text.strip():
            print("No embedded text found. Triggering EasyOCR engine...")
            reader = get_ocr_reader()
            for page_index in range(len(doc)):
                page = doc[page_index]
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                results = reader.readtext(img_bytes, detail=0)
                extracted_text += " ".join(results) + "\n"

        if not extracted_text.strip():
            raise ValueError("Failed to extract any text or OCR data from the PDF file.")

        document_id = f"pdf_{filename}_{uuid.uuid4().hex[:4]}"
        return self.process_and_store(extracted_text, user_id=user_id, document_id=document_id)

    def process_docx_file(self, file_bytes: bytes, filename: str, user_id: str) -> dict:
        """
        Extracts text from Word (.docx) documents.
        """
        doc = docx.Document(io.BytesIO(file_bytes))
        full_text = [para.text for para in doc.paragraphs if para.text.strip()]
        extracted_text = "\n".join(full_text)

        if not extracted_text.strip():
            raise ValueError("The Word document appears to be empty.")

        document_id = f"docx_{filename}_{uuid.uuid4().hex[:4]}"
        return self.process_and_store(extracted_text, user_id=user_id, document_id=document_id)

    def process_txt_file(self, file_bytes: bytes, filename: str, user_id: str) -> dict:
        """
        Extracts text from plain text (.txt) files.
        """
        extracted_text = file_bytes.decode("utf-8", errors="ignore")
        if not extracted_text.strip():
            raise ValueError("The text file is empty.")

        document_id = f"txt_{filename}_{uuid.uuid4().hex[:4]}"
        return self.process_and_store(extracted_text, user_id=user_id, document_id=document_id)

    def search_similar_chunks(self, query: str, user_id: str, top_k: int = 5):
        """
        Retrieves top_k relevant text chunks from vector store filtered strictly by user_id.
        """
        results = self.vector_store.similarity_search_with_score(
            query, 
            k=top_k,
            filter={"user_id": user_id}
        )
        
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": float(score)
            })

        return formatted_results

    def generate_answer(self, query: str, user_id: str, history: list = None):
        """
        Executes full RAG workflow with conversational history memory.
        """
        search_results = self.search_similar_chunks(query, user_id=user_id, top_k=5)
        
        if not search_results:
            return {
                "answer": "No relevant information found in your knowledge base.",
                "sources": []
            }

        context_text = "\n---\n".join([item["content"] for item in search_results])

        # Μορφοποίηση του ιστορικού συνομιλίας (αν υπάρχει)
        formatted_history = ""
        if history:
            for msg in history[-6:]:  # Παίρνουμε τα τελευταία 6 μηνύματα για context
                role_label = "User" if msg.get("role") == "user" else "Assistant"
                formatted_history += f"{role_label}: {msg.get('content')}\n"

        system_prompt = (
            "You are an expert HR and document analysis AI assistant.\n"
            "Analyze the provided context carefully and answer the user question thoroughly in Greek.\n"
            "Take into consideration the recent chat history to understand follow-up questions.\n"
            "If the context contains details about a candidate, resume, or document, summarize them accurately.\n"
            "If the question cannot be answered from the context at all, state that information is missing.\n\n"
            "IMPORTANT: You must ALWAYS respond exclusively in ENGLISH, maintaining a clear, professional, and helpful tone.\n\n"
            f"--- RECENT CHAT HISTORY ---\n{formatted_history if formatted_history else 'No previous context.'}\n\n"
            f"--- CONTEXT START ---\n{context_text}\n--- CONTEXT END ---\n\n"
            f"Question: {query}\n"
            f"Answer:"
        )

        response = self.llm.invoke(system_prompt)

        return {
            "answer": response.content,
            "sources": [item["content"] for item in search_results]
        }

    def get_user_documents(self, user_id: str):
        """
        Retrieves unique document IDs uploaded by the specific user.
        """
        results = self.vector_store.get(where={"user_id": user_id})
        metadatas = results.get("metadatas", [])
        
        unique_docs = {}
        for meta in metadatas:
            doc_id = meta.get("document_id", "Unknown")
            if doc_id not in unique_docs:
                doc_type = "PDF" if doc_id.startswith("pdf_") else "DOCX" if doc_id.startswith("docx_") else "TXT" if doc_id.startswith("txt_") else "Text Note"
                unique_docs[doc_id] = {
                    "document_id": doc_id,
                    "type": doc_type
                }
                
        return list(unique_docs.values())

    def delete_document(self, user_id: str, document_id: str):
        """
        Deletes all vector chunks associated with a specific document_id for the given user_id.
        """
        results = self.vector_store.get(where={"user_id": user_id})
        ids_to_delete = []
        
        if results and "ids" in results and "metadatas" in results:
            for item_id, meta in zip(results["ids"], results["metadatas"]):
                if meta.get("document_id") == document_id:
                    ids_to_delete.append(item_id)

        if ids_to_delete:
            self.vector_store.delete(ids=ids_to_delete)
            return True
        return False