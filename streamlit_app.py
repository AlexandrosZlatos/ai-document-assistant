import streamlit as st
import requests

st.set_page_config(page_title="AI SaaS Knowledge Base", page_icon="🤖", layout="wide")
API_URL = "http://127.0.0.1:8000/api/v1"

if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.token:
    st.title("🔐 Welcome to AI SaaS")
    tab_login, tab_register = st.tabs(["Login", "Register"])
    
    with tab_login:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In"):
            if not username or not password:
                st.warning("Please fill in both fields.")
            else:
                res = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.token = data["token"]
                    st.session_state.username = data["username"]
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                
    with tab_register:
        reg_username = st.text_input("Username", key="reg_user")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Sign Up"):
            if not reg_username or not reg_password:
                st.warning("Please fill in both fields.")
            else:
                res = requests.post(f"{API_URL}/register", json={"username": reg_username, "password": reg_password})
                if res.status_code == 200:
                    st.success("Account created successfully! You can now log in.")
                else:
                    st.error(res.json().get("detail", "Registration failed."))

else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    
    with st.sidebar:
        st.write(f"👤 Logged in as: **{st.session_state.username}**")
        
        col_logout, col_clear = st.columns(2)
        with col_logout:
            if st.button("Logout"):
                st.session_state.token = None
                st.session_state.username = None
                st.session_state.messages = []
                st.rerun()
        with col_clear:
            if st.button("🧹 Clear Chat"):
                st.session_state.messages = []
                st.rerun()
            
        st.divider()
        st.header("📄 Add Knowledge")
        tab1, tab2 = st.tabs(["Upload Document", "Paste Text"])
        
        with tab1:
            uploaded_file = st.file_uploader("Choose File (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
            if st.button("Process Document"):
                if uploaded_file:
                    with st.spinner("Processing document..."):
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        res = requests.post(f"{API_URL}/documents/upload-file", files=files, headers=headers)
                        if res.status_code == 200:
                            st.success("Document processed successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to process document: {res.json().get('detail', 'Error')}")
                else:
                    st.warning("Please upload a file first.")
                        
        with tab2:
            doc_text = st.text_area("Paste text:")
            if st.button("Upload Text"):
                if doc_text.strip():
                    with st.spinner("Storing text..."):
                        res = requests.post(f"{API_URL}/documents", json={"content": doc_text}, headers=headers)
                        if res.status_code == 200:
                            st.success("Text stored successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to store text.")
                else:
                    st.warning("Please paste some text first.")

        st.divider()
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            st.header("📁 Documents")
        with col_btn:
            if st.button("🔄"):
                st.rerun()

        try:
            docs_res = requests.get(f"{API_URL}/documents", headers=headers)
            if docs_res.status_code == 200:
                docs = docs_res.json().get("data", [])
                if docs:
                    for doc in docs:
                        icon = "📄" if doc["type"] in ["PDF", "DOCX", "TXT"] else "📝"
                        col_doc, col_del = st.columns([4, 1])
                        with col_doc:
                            st.markdown(f"**{icon} {doc['document_id']}**")
                        with col_del:
                            if st.button("🗑️", key=f"del_{doc['document_id']}"):
                                del_res = requests.delete(f"{API_URL}/documents/{doc['document_id']}", headers=headers)
                                if del_res.status_code == 200:
                                    st.toast(f"Deleted: {doc['document_id']}")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete document.")
                else:
                    st.info("No documents found.")
            else:
                st.error(f"API Error: {docs_res.status_code}")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")

    st.title("🤖 AI SaaS Knowledge Base")
    st.caption("Ask questions strictly based on your uploaded documents.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if user_query := st.chat_input("Ask something about your uploaded documents..."):
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base & generating answer..."):
                try:
                    payload = {
                        "question": user_query,
                        "history": st.session_state.messages
                    }
                    res = requests.post(f"{API_URL}/chat", json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json().get("data", {})
                        answer = data.get("answer", "No response received.")
                        st.write(answer)
                        
                        sources = data.get("sources", [])
                        if sources:
                            with st.expander("Show retrieved context sources"):
                                for idx, src in enumerate(sources, 1):
                                    st.markdown(f"**Source {idx}:**\n> {src}")

                        st.session_state.messages.append({"role": "user", "content": user_query})
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        error_msg = res.json().get("detail", "Error retrieving response.")
                        st.error(f"Error: {error_msg}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")