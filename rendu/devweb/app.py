import json
import requests
import streamlit as st

OLLAMA_URL = "http://localhost:11434"
MODEL = "finance-bot"

st.set_page_config(page_title="TechCorp Financial Assistant", page_icon="💰")

def server_online():
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).status_code == 200
    except requests.RequestException:
        return False

def stream_chat(messages):
    with requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": MODEL, "messages": messages, "stream": True},
        stream=True, timeout=120,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line).get("message", {}).get("content", "")
            if chunk:
                yield chunk

st.title("💰 TechCorp Financial Assistant")

online = server_online()
if online:
    st.success("🟢 Connecté au serveur d'inférence (Ollama)")
else:
    st.error("🔴 Déconnecté — serveur Ollama injoignable sur :11434")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Posez votre question financière…", disabled=not online)
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            full = st.write_stream(stream_chat(st.session_state.messages))
        except requests.RequestException as e:
            full = f"⚠️ Erreur de connexion au serveur : {e}"
            st.error(full)
    st.session_state.messages.append({"role": "assistant", "content": full})
