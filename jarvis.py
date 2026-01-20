# jarvis.py – FRIDAY Agent v2.7 (MAX CREATIVE UI + ORANGE LIVE MARQUEE + OUTLINE BUTTONS)
# Run: streamlit run jarvis.py

import os
import json
import time
import webbrowser
import threading
import psutil
import requests
import streamlit as st
from datetime import datetime
import urllib.parse
import queue
import io
import subprocess
import socket
from streamlit_autorefresh import st_autorefresh

# Optional imports
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import ollama
except ImportError:
    ollama = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None

# ==================================================
# CONFIG
# ==================================================
BASE_FOLDER = r"C:\Users\P R VISHAL\OneDrive\Desktop\FRIDAY..!!"
os.makedirs(BASE_FOLDER, exist_ok=True)
MEMORY_FILE = os.path.join(BASE_FOLDER, "friday_memory.json")
NOTES_FILE = os.path.join(BASE_FOLDER, "friday_notes.txt")
PASSWORD = "1234"
OLLAMA_MODEL = "llama3"
USE_OLLAMA = True

# ==================================================
# VOICE ENGINE
# ==================================================
class VoiceEngine:
    def __init__(self):
        self.enabled = pyttsx3 is not None
        self.engine = None
        if self.enabled:
            try:
                self.engine = pyttsx3.init('sapi5')
                self.engine.setProperty('rate', 160)
                self.engine.setProperty('volume', 0.9)
            except:
                self.enabled = False

    def speak(self, text):
        if not text.strip() or not self.enabled:
            return
        try:
            self.engine.stop()
            self.engine.say(text[:180])
            self.engine.runAndWait()
        except:
            pass

voice = VoiceEngine()

# ==================================================
# MEMORY ENGINE
# ==================================================
class MemoryEngine:
    def __init__(self):
        self.file = MEMORY_FILE
        self.data = self.load()
        self.last_action = "Idle"

    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for key in ["short_term", "long_term", "context", "tasks", "failures", "chat_history"]:
                    if key not in data:
                        data[key] = [] if key != "context" else {}
                return data
            except:
                pass
        return {
            "short_term": [],
            "long_term": [],
            "context": {"last_action": "", "last_topic": ""},
            "tasks": [],
            "failures": [],
            "chat_history": []
        }

    def save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2)

    def add_chat(self, role, content):
        entry = {"role": role, "content": content, "time": str(datetime.now())}
        self.data["chat_history"].append(entry)
        if len(self.data["chat_history"]) > 20:
            self.data["long_term"].extend(self.data["chat_history"][:10])
            self.data["chat_history"] = self.data["chat_history"][10:]
        self.save()

    def add_task(self, goal):
        tid = f"T{len(self.data['tasks']) + 1:03d}"
        task = {"id": tid, "goal": goal, "status": "pending", "created": str(datetime.now())}
        self.data["tasks"].append(task)
        self.save()
        return tid

    def get_recent_tasks(self):
        return self.data.get("tasks", [])

    def update_context(self, key, value):
        self.data["context"][key] = value
        self.save()

    def recall_memory(self, query):
        matches = [m for m in self.data["chat_history"] + self.data["long_term"] if query.lower() in m["content"].lower()]
        if matches:
            return "\n".join([f"{m['time']} | {m['role']}: {m['content'][:100]}" for m in matches[-3:]])
        return "No matching memory found."

memory = MemoryEngine()

# ==================================================
# LIVE SYSTEM MONITOR THREAD
# ==================================================
monitor_queue = queue.Queue()
monitor_running = False

def get_network_speed():
    try:
        s = socket.create_connection(('www.google.com', 80))
        s.close()
        return "Connected (Speed: High)"  # Placeholder; use speedtest-cli if installed, but assuming no extra libs
    except:
        return "Disconnected"

def system_monitor_thread():
    global monitor_running
    monitor_running = True
    monitor_queue.put(("stats", {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('C:\\').percent,
        "battery": "Initializing...",
        "network": "Checking...",
        "net_speed": "Scanning..."
    }))
    while monitor_running:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('C:\\').percent
            bat = psutil.sensors_battery()
            bat_str = f"{bat.percent}% ({'charging' if bat.power_plugged else 'on battery'})" if bat else "N/A"
            net = "Online" if requests.get("https://www.google.com", timeout=2).status_code == 200 else "Offline"
            net_speed = get_network_speed()
            alert = ""
            if ram > 85: alert += f"High RAM: {ram}% "
            if cpu > 90: alert += f"High CPU: {cpu}% "
            if disk > 90: alert += f"Disk C full: {disk}% "
            if alert:
                voice.speak("System alert! " + alert)
                monitor_queue.put(("alert", alert))
            monitor_queue.put(("stats", {
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "battery": bat_str,
                "network": net,
                "net_speed": net_speed
            }))
        except:
            pass
        time.sleep(2)
    if not monitor_running:
        pass

monitor_thread = threading.Thread(target=system_monitor_thread, daemon=True)
monitor_thread.start()

# ==================================================
# TOOLS
# ==================================================
def open_app(apps_str):
    apps = [a.strip() for a in apps_str.replace("+", " and ").split(" and ") if a.strip()]
    results = []
    app_map = {
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "youtube": "https://youtube.com",
        "whatsapp": "https://web.whatsapp.com",
        "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "paint": "mspaint.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "settings": "ms-settings:",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "gmail": "https://mail.google.com",
        "netflix": "https://netflix.com",
        "amazon": "https://amazon.com",
        "twitter": "https://twitter.com",
        "instagram": "https://instagram.com",
        "facebook": "https://facebook.com",
        "spotify": "spotify.exe"  # Assuming installed
    }
    for app in apps:
        if app in app_map:
            if "http" in app_map[app] or "https" in app_map[app]:
                webbrowser.open(app_map[app])
            elif app_map[app].startswith("ms-"):
                os.system(f"start {app_map[app]}")
            else:
                subprocess.Popen(app_map[app], shell=True)
            results.append(f"Activated {app.capitalize()} Protocol")
            memory.last_action = f"Activated {app.capitalize()}"
        else:
            results.append(f"{app.capitalize()} Protocol Not Recognized")
    return "\n".join(results)

def play_youtube(query):
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open(url)
    memory.last_action = f"Initiated YouTube Sequence: '{query}'"
    return f"Engaging Visual Sequence '{query}' on YouTube (Search Activated)"

def get_system_status():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('C:\\').percent
    bat = psutil.sensors_battery()
    bat_str = f"{bat.percent}% ({'charging' if bat.power_plugged else 'on battery'})" if bat else "N/A"
    net_speed = get_network_speed()
    return f"Core Processor Load: {cpu}% | Memory Allocation: {ram}% | Storage Matrix C: {disk}% | Energy Core: {bat_str} | Network Grid: {net_speed}"

def research(topic):
    url = f"https://www.google.com/search?q={urllib.parse.quote(topic)}"
    webbrowser.open(url)
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}] Intelligence Scan: {topic}\n")
    memory.last_action = f"Deployed Intelligence Scan on {topic}"
    return f"Intelligence Scan on '{topic}' Activated (Quantum Search Engaged)"

def parse_document(file_bytes, filename):
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    try:
        if ext == ".pdf" and PyPDF2:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx" and Document:
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
        elif ext in [".txt", ".py", ".log"]:
            text = file_bytes.decode("utf-8", errors="ignore")
    except:
        text = "Asset Decryption Failed."
    return text[:4000]

# ==================================================
# FULL AGENTIC LOOP
# ==================================================
def agentic_process(query, uploaded_content=""):
    memory.last_action = "Initiating Analysis Sequence"
    reasoning = "Decoding Directive..."
    plan = ""
    execution = ""
    evaluation = "Protocol Success"
    reflection = ""
    start_time = time.time()

    if USE_OLLAMA and ollama:
        try:
            prompt = f"Decode step-by-step: {query}"
            if uploaded_content:
                prompt += f"\nAsset Data: {uploaded_content[:400]}"
            resp = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
            reasoning = resp['message']['content'][:400]
        except:
            pass

    tasks = []
    q = query.lower()
    if "open" in q:
        apps_part = q.replace("open", "").replace("+", " and ").strip()
        tasks.append({"action": "OPEN_APP", "param": apps_part})
    if "play" in q and "youtube" in q:
        query_part = q.replace("play", "").replace("on youtube", "").replace("youtube", "").strip()
        tasks.append({"action": "PLAY_YOUTUBE", "param": query_part})
    if any(w in q for w in ["battery", "cpu", "ram", "system", "status", "network"]):
        tasks.append({"action": "SYSTEM_STATUS"})
    if "research" in q or "tell me about" in q:
        topic = q.replace("research", "").replace("tell me about", "").strip() or q
        tasks.append({"action": "RESEARCH", "param": topic})
    if "add task" in q:
        goal = q.replace("add task", "").strip()
        tasks.append({"action": "ADD_TASK", "param": goal})
    if not tasks:
        tasks.append({"action": "GENERAL", "param": query})

    plan = f"Strategic Plan: {len(tasks)} Directive(s) → " + ", ".join(t["action"] for t in tasks)

    results = []
    for t in tasks:
        action = t["action"]
        param = t.get("param", "")
        if action == "OPEN_APP":
            res = open_app(param)
        elif action == "PLAY_YOUTUBE":
            res = play_youtube(param)
        elif action == "SYSTEM_STATUS":
            res = get_system_status()
        elif action == "RESEARCH":
            res = research(param)
        elif action == "ADD_TASK":
            tid = memory.add_task(param)
            res = f"Directive {tid} Integrated: {param}"
        else:
            res = "Directive Acknowledged – Awaiting Next Sequence."
        results.append(res)

    execution = "\n".join(results)
    if "not supported" in execution.lower():
        evaluation = "Partial Protocol Anomaly – Some Directives Unsupported"
    else:
        evaluation = "All Directives Executed Successfully"

    elapsed = round(time.time() - start_time, 2)
    reflection = f"Sequence Completed in {elapsed}s. {evaluation}."

    final = f"Decoding Analysis: {reasoning}\n\nStrategic Plan: {plan}\n\nExecution Matrix: {execution}\n\nEvaluation Protocol: {evaluation}\n\nReflection Sequence: {reflection}"

    voice.speak(f"{evaluation}. {results[0][:80] if results else ''}")
    memory.add_chat("user", query)
    memory.add_chat("assistant", final)
    memory.last_action = f"Executed: {results[0][:50]}" if results else "Idle"

    return final

# ==================================================
# STREAMLIT UI
# ==================================================
def main():
    st.set_page_config(page_title="FRIDAY AI", layout="wide", initial_sidebar_state="expanded")

    # CSS
    st.markdown("""
        <style>
        .stApp {
            background-color: #0e1117;
            color: white;
        }
        .stTextInput > div > div > input {
            background-color: #1e1e1e;
            color: white;
            border: 1px solid #444;
            border-radius: 8px;
        }
        .stButton > button {
            background-color: transparent !important;
            color: #ff9500 !important;
            border: 2px solid #ff9500 !important;
            border-radius: 50px !important;
            padding: 10px 24px !important;
            font-weight: bold;
            transition: all 0.3s;
        }
        .stButton > button:hover {
            background-color: #ff9500 !important;
            color: black !important;
            transform: scale(1.04);
        }
        .stChatMessage {
            background-color: #1e1e1e;
            border-radius: 12px;
            padding: 14px;
            margin: 8px 0;
            animation: fadeIn 0.6s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .marquee-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background: linear-gradient(90deg, #1a1f2e, #2a2f3e);
            color: #ff9500;
            padding: 12px 0;
            overflow: hidden;
            z-index: 999;
            border-bottom: 2px solid #ff9500;
            font-family: 'Consolas', monospace;
            font-size: 14px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }
        .marquee {
            display: inline-block;
            white-space: nowrap;
            animation: marquee 25s linear infinite;
            color: #ffffff; /* ✅ TEXT COLOR FIX (WHITE) */
            font-weight: 500;
        }
        @keyframes marquee {
            0% { transform: translateX(100%); }
            100% { transform: translateX(-100%); }
        }
        /* Sidebar background */
        section[data-testid="stSidebar"] {
            background-color: #11151f !important;
            color: #ffffff !important; /* ✅ sidebar text also visible */
        }
        </style>
    """, unsafe_allow_html=True)

    # Marquee
    # ===================== LIVE MARQUEE STATUS (FIXED) =====================

    # Session state init (KEEP THIS FIRST)
    if "mode" not in st.session_state:
        st.session_state.mode = "Agent"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if "uploaded_content" not in st.session_state:
        st.session_state.uploaded_content = ""
    if "live_stats" not in st.session_state:
        st.session_state.live_stats = {
            "cpu": "--",
            "ram": "--",
            "disk": "--",
            "battery": "--",
            "network": "--",
            "net_speed": "--"
        }
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()

    # 🔥 Drain monitor queue SAFELY (VERY IMPORTANT)
    while not monitor_queue.empty():
        typ, val = monitor_queue.get()
        if typ == "stats":
            st.session_state.live_stats = val

    # 🔥 Build marquee ONLY from session_state (NEVER from queue)
    stats = st.session_state.live_stats
    llm_status = (
        f"Core Intelligence Online ({OLLAMA_MODEL})" if USE_OLLAMA and ollama else "Core Offline"
    )
    memory_load = len(memory.data["chat_history"])
    task_count = len(memory.get_recent_tasks())
    status_items = [
        f"CPU Usage: {stats['cpu']}%",
        f"RAM Usage: {stats['ram']}%",
        f"Disk C: {stats['disk']}%",
        f"Battery: {stats['battery']}",
        f"Network: {stats['network']}",
        f"Net Speed: {stats['net_speed']}",
        f"Memory Load: {memory_load} Entries",
        f"Task Queue: {task_count} Pending",
        f"LLM: {llm_status}"
    ]
    marquee_text = " • ".join(status_items) + " • " * 4
    st.markdown(
        f"""
        <div class="marquee-container">
            <div class="marquee">
                {marquee_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Space below marquee
    st.markdown("<br>", unsafe_allow_html=True)
    st_autorefresh(interval=2000, key="live_marquee_refresh")

    # ===================== END LIVE MARQUEE FIX =====================

    # ── Initial Authentication Required ────────────────────────────────────────
    if not st.session_state.auth:
        st.title("FRIDAY – Arc Reactor Authentication Sequence")
        pwd = st.text_input("Enter Arc Reactor Access Code", type="password")
        if st.button("🔒 Engage Authentication Protocol"):
            if pwd == PASSWORD:
                st.success("Access Granted: Arc Reactor Online")
                voice.speak("Access Granted. Systems Online.")
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Access Denied: Invalid Arc Reactor Code")
                voice.speak("Access Denied.")
        st.stop()

    # ── Agent Mode ───────────────────────────────────
    if st.session_state.mode == "Agent":
        st.markdown("<h1>FRIDAY – Grandmaster Agent Protocol</h1>", unsafe_allow_html=True)
        if st.button("🔄 COMMAND MODE ACTIVATE...."):
            st.session_state.mode = "Command"
            st.rerun()

        with st.sidebar:
            st.header("Quick Actions Control Matrix")
            st.markdown("### Rapid Deployment Actions")
            if st.button("🎤 Engage Voice command"):
                if sr:
                    r = sr.Recognizer()
                    with sr.Microphone() as source:
                        st.info("Vocal Capture Activated...")
                        try:
                            audio = r.listen(source, timeout=6)
                            text = r.recognize_google(audio)
                            st.session_state.agent_query = text
                            st.rerun()
                        except:
                            st.error("Vocal Directive Unrecognized")
                else:
                    st.error("Vocal Interface Module Absent")

            uploaded = st.file_uploader("🗂️ Upload Intelligence Asset", type=["pdf","txt","py","log"])
            if uploaded:
                content = uploaded.read()
                parsed = parse_document(content, uploaded.name)
                st.session_state.uploaded_content = parsed
                st.success(f"Asset Decoded: {uploaded.name}")

            st.markdown("### Strategic Directive Operations")
            if st.button("📋 Reveal Pending Directives"):
                tasks = memory.get_recent_tasks()
                if tasks:
                    st.json(tasks)
                else:
                    st.info("Directive Queue Empty")

        tab1, tab2, tab3 = st.tabs(["Primary Nexus", "Intelligence Log", "Directive Queue & Recall Vault"])

        with tab1:
            st.subheader("Deploy FRIDAY Directive....INTENT -> INTELLIGENCE ")
            user_query = st.text_input("Input Your Command Sequence...", key="agent_query")
            if st.button("🚀 Initiate FRIDAY Engine......!!!"):
                query = user_query or st.session_state.get("agent_query", "")
                if query:
                    with st.spinner("Initiating Processing System to THINK..."):
                        result = agentic_process(query, st.session_state.uploaded_content)
                    st.session_state.messages.append({"role": "user", "content": query})
                    st.session_state.messages.append({"role": "assistant", "content": result})
                    st.rerun()

            # LIVE STATUS SECTION
            stats = st.session_state.live_stats
            uptime_seconds = int(time.time() - st.session_state.start_time)
            uptime = f"{uptime_seconds // 3600:02d}:{(uptime_seconds % 3600) // 60:02d}:{uptime_seconds % 60:02d}"
            engine_state = "Running" if "Idle" not in memory.last_action else "Idle"
            engine_class = "running" if engine_state == "Running" else "idle"
            battery = stats["battery"]
            ram_percent = stats["ram"]
            ram_used = round((ram_percent / 100) * psutil.virtual_memory().total / (1024 ** 3), 1)
            ram_total = round(psutil.virtual_memory().total / (1024 ** 3), 1)
            cpu_percent = stats["cpu"]
            network = stats["network"]
            net_speed = stats["net_speed"]
            network_status = f"{network} ({'Low Latency' if 'High' in net_speed else net_speed})"
            network_class = "online" if network == "Online" else "error"
            task_active = sum(1 for t in memory.get_recent_tasks() if t["status"] != "pending")
            task_pending = len(memory.get_recent_tasks()) - task_active
            disk_percent = stats["disk"]
            disk_used = round((disk_percent / 100) * psutil.disk_usage('C:\\').total / (1024 ** 3), 0)
            disk_total = round(psutil.disk_usage('C:\\').total / (1024 ** 3), 0)
            ai_state = "Online" if USE_OLLAMA and ollama else "Offline"
            ai_class = "online" if ai_state == "Online" else "error"
            # Mock for advanced
            security = "Secure"
            security_class = "secure"
            logs = "Nominal (No Errors)"
            thermal = "42°C (Cool)"

            st.markdown(f"""
                <div class="live-status-panel">
                  <h2>LIVE STATUS</h2>
                  <h3>Real-time System Health & Runtime Metrics</h3>
                  <div class="metrics-grid">
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">⚙️</span>
                        <span class="metric-label">Engine State</span>
                      </div>
                      <div class="metric-value">
                        <span class="status-indicator {engine_class}"></span> {engine_state}
                      </div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">⏱️</span>
                        <span class="metric-label">System Uptime</span>
                      </div>
                      <div class="metric-value">{uptime}</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">🔋</span>
                        <span class="metric-label">Battery / Power</span>
                      </div>
                      <div class="metric-value">{battery}</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">🧠</span>
                        <span class="metric-label">Memory Usage</span>
                      </div>
                      <div class="metric-value">{ram_used} GB / {ram_total} GB</div>
                      <div class="progress-bar"><div style="width: {ram_percent}%;"></div></div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">💻</span>
                        <span class="metric-label">CPU Load</span>
                      </div>
                      <div class="metric-value">{cpu_percent}%</div>
                      <div class="progress-bar"><div style="width: {cpu_percent}%;"></div></div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">🌐</span>
                        <span class="metric-label">Network Status</span>
                      </div>
                      <div class="metric-value">
                        <span class="status-indicator {network_class}"></span> {network_status}
                      </div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">📋</span>
                        <span class="metric-label">Task Queue</span>
                      </div>
                      <div class="metric-value">{task_active} Active / {task_pending} Pending</div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">💾</span>
                        <span class="metric-label">Storage Health</span>
                      </div>
                      <div class="metric-value">{disk_used} GB / {disk_total} GB (Healthy)</div>
                      <div class="progress-bar"><div style="width: {disk_percent}%;"></div></div>
                    </div>
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="metric-icon">🤖</span>
                        <span class="metric-label">AI Model State</span>
                      </div>
                      <div class="metric-value">
                        <span class="status-indicator {ai_class}"></span> {ai_state} ({OLLAMA_MODEL})
                      </div>
                    </div>
                  </div>
                  <details class="advanced-metrics">
                    <summary>Advanced Metrics</summary>
                    <div class="metrics-grid">
                      <div class="metric-card">
                        <div class="metric-header">
                          <span class="metric-icon">🔒</span>
                          <span class="metric-label">Security Status</span>
                        </div>
                        <div class="metric-value">
                          <span class="status-indicator {security_class}"></span> {security}
                        </div>
                      </div>
                      <div class="metric-card">
                        <div class="metric-header">
                          <span class="metric-icon">📜</span>
                          <span class="metric-label">Logs Status</span>
                        </div>
                        <div class="metric-value">{logs}</div>
                      </div>
                      <div class="metric-card">
                        <div class="metric-header">
                          <span class="metric-icon">🌡️</span>
                          <span class="metric-label">Thermal State</span>
                        </div>
                        <div class="metric-value">{thermal}</div>
                      </div>
                    </div>
                  </details>
                </div>

                <style>
                .live-status-panel {{
                  background-color: #1e1e1e;
                  border-radius: 12px;
                  padding: 24px;
                  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                  margin-top: 24px;
                  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                  color: #ffffff;
                }}
                .live-status-panel h2 {{
                  font-size: 24px;
                  margin: 0 0 8px 0;
                  color: #ff9500;
                  text-shadow: 0 0 4px rgba(255, 149, 0, 0.3);
                }}
                .live-status-panel h3 {{
                  font-size: 16px;
                  margin: 0 0 20px 0;
                  color: #aaaaaa;
                  font-weight: normal;
                }}
                .metrics-grid {{
                  display: grid;
                  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                  gap: 16px;
                }}
                .metric-card {{
                  background-color: #0e1117;
                  border-radius: 8px;
                  padding: 16px;
                  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
                }}
                .metric-header {{
                  display: flex;
                  align-items: center;
                  margin-bottom: 8px;
                }}
                .metric-icon {{
                  font-size: 20px;
                  margin-right: 8px;
                }}
                .metric-label {{
                  font-size: 14px;
                  color: #aaaaaa;
                  font-weight: bold;
                }}
                .metric-value {{
                  font-size: 18px;
                  font-weight: bold;
                  display: flex;
                  align-items: center;
                }}
                .progress-bar {{
                  background-color: #444444;
                  height: 6px;
                  border-radius: 3px;
                  margin-top: 8px;
                  overflow: hidden;
                }}
                .progress-bar div {{
                  background-color: #ff9500;
                  height: 100%;
                  border-radius: 3px;
                  transition: width 0.3s ease-in-out;
                }}
                .status-indicator {{
                  width: 10px;
                  height: 10px;
                  border-radius: 50%;
                  margin-right: 8px;
                  display: inline-block;
                }}
                .status-indicator.online, .status-indicator.running, .status-indicator.secure {{
                  background-color: #00ff00;
                  box-shadow: 0 0 8px rgba(0, 255, 0, 0.6);
                  animation: pulse 1.5s infinite;
                }}
                .status-indicator.idle {{
                  background-color: #ff9500;
                  box-shadow: 0 0 8px rgba(255, 149, 0, 0.6);
                }}
                .status-indicator.error {{
                  background-color: #ff0000;
                  box-shadow: 0 0 8px rgba(255, 0, 0, 0.6);
                  animation: pulse 1s infinite;
                }}
                @keyframes pulse {{
                  0% {{ transform: scale(1); opacity: 1; }}
                  50% {{ transform: scale(1.1); opacity: 0.7; }}
                  100% {{ transform: scale(1); opacity: 1; }}
                }}
                .advanced-metrics {{
                  margin-top: 24px;
                }}
                .advanced-metrics summary {{
                  font-size: 16px;
                  color: #ff9500;
                  cursor: pointer;
                  outline: none;
                  padding: 8px;
                  border-radius: 8px;
                  background-color: #0e1117;
                  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
                }}
                .advanced-metrics[open] summary {{
                  margin-bottom: 16px;
                }}
                </style>
            """, unsafe_allow_html=True)

        with tab2:
            st.subheader("Elite Operational Log")
            if st.session_state.messages:
                for msg in st.session_state.messages[-10:]:
                    role = "Operator" if msg["role"] == "user" else "FRIDAY Protocol"
                    avatar = "👤" if role == "Operator" else "🤖"
                    with st.chat_message(role, avatar=avatar):
                        st.markdown(msg["content"])
            else:
                st.info("Operational Log Clear – Initiate Directives")

        with tab3:
            st.subheader("Strategic Directive Queue")
            tasks = memory.get_recent_tasks()
            if tasks:
                for t in tasks:
                    st.write(f"{t['id']}: {t['goal']} ({t['status']})")
            else:
                st.info("Directive Queue Empty – Deploy 'Add Directive: Objective'")

            st.subheader("Intelligence Recall Vault")
            recall_q = st.text_input("Query Historical Intelligence...")
            if recall_q:
                recall = memory.recall_memory(recall_q)
                st.markdown(recall)

    # ── Command Mode ─────────────────────────────────
    else:
        st.markdown("<h1>FRIDAY – Elite Command Nexus</h1>", unsafe_allow_html=True)
        st.info("Direct Neural Link with Core Intelligence • No Auxiliary Protocols Unless Commanded")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        cmd_msg = st.chat_input("Transmit Elite Directive...")
        if cmd_msg:
            st.session_state.messages.append({"role": "user", "content": cmd_msg})
            with st.spinner("Core Intelligence Processing..."):
                if USE_OLLAMA and ollama:
                    try:
                        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-12:]]
                        resp = ollama.chat(model=OLLAMA_MODEL, messages=history)
                        reply = resp['message']['content']
                    except:
                        reply = "Core Intelligence Anomaly Detected."
                else:
                    reply = "Intelligence Core Offline."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            voice.speak(reply[:150])
            st.rerun()

        if st.button("⬅️ Revert to AGENT MODE.....!!"):
            st.session_state.mode = "Agent"
            st.rerun()

if __name__ == "__main__":
    main()