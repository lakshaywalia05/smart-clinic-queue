import sqlite3
import socket
import qrcode
import os
import uuid
import webbrowser
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_FILE = 'clinic_demo.db'

# Generate a unique Session ID when the app starts
CURRENT_SESSION_ID = str(uuid.uuid4())

# ==========================================
#  🌑 1. DARK MODE PATIENT UI (With Branding)
# ==========================================
patient_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinic Check-In</title>
    <style>
        :root {
            --primary: #6366f1; /* Indigo */
            --bg: #111827;      /* Very Dark Grey */
            --card: #1f2937;    /* Dark Grey Card */
            --text: #f3f4f6;
            --subtext: #9ca3af;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            margin: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            color: var(--text);
        }
        
        /* 🔥 BRANDING HEADER 🔥 */
        .branding {
            margin-top: 20px;
            font-size: 12px;
            font-weight: bold;
            letter-spacing: 2px;
            color: var(--primary);
            text-transform: uppercase;
            opacity: 0.8;
            margin-bottom: 10px;
        }

        .container { width: 100%; max-width: 400px; padding: 20px; }
        
        .card {
            background: var(--card);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            text-align: center;
            border: 1px solid #374151;
        }
        h1 { font-size: 22px; margin-bottom: 5px; color: var(--text); }
        p { color: var(--subtext); font-size: 14px; margin-top: 0; }
        
        .token-display {
            background: #111827;
            color: var(--primary);
            font-size: 64px;
            font-weight: 800;
            border-radius: 20px;
            padding: 20px;
            margin: 20px 0;
            border: 2px solid #374151;
        }

        input {
            width: 100%; padding: 16px; background: #111827; border: 2px solid #374151;
            color: white; border-radius: 12px; font-size: 16px; outline: none;
            box-sizing: border-box; text-align: center; margin-bottom: 15px;
        }
        input:focus { border-color: var(--primary); }

        .btn {
            background: var(--primary); color: white; border: none; width: 100%;
            padding: 16px; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer;
        }
        .btn:active { opacity: 0.8; }

        .status-badge {
            display: inline-block; padding: 6px 12px; border-radius: 20px;
            font-size: 12px; font-weight: 600; margin-bottom: 10px;
        }
        .waiting { background: #3730a3; color: #c7d2fe; }
        .serving { background: #064e3b; color: #6ee7b7; }
        
        .icon { width: 40px; height: 40px; margin-bottom: 10px; fill: var(--primary); }
    </style>
</head>
<body>

    <div class="branding">MADE BY LAKSHAY WALIA</div>

    <div class="container">
        <div id="booking-view" class="card">
            <svg class="icon" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M8 9a3 3 0 100-6 3 3 0 000 6zM8 11a6 6 0 016 6H2a6 6 0 016-6zM16 7a1 1 0 10-2 0v1h-1a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V7z"/></svg>
            <h1>Check In</h1>
            <p>Enter your name to join the queue.</p>
            
            <div style="margin: 20px 0;">
                <span style="font-size:12px; text-transform:uppercase; color:#6b7280;">Now Serving Token</span>
                <div id="live-token-display" style="font-size: 30px; font-weight:bold; color:white;">--</div>
            </div>

            <input type="text" id="p-name" placeholder="Your Full Name">
            <button class="btn" onclick="bookToken()">Get Token</button>
        </div>

        <div id="status-view" class="card" style="display:none;">
            <div id="status-badge" class="status-badge waiting">WAITING</div>
            <h1 id="user-name">Guest</h1>
            <p>Your Token Number</p>
            
            <div id="my-token" class="token-display">--</div>
            
            <div style="border-top: 1px solid #374151; padding-top: 20px; margin-top: 20px;">
                <p>People ahead of you</p>
                <h2 id="people-ahead" style="font-size:24px; margin:5px 0; color:#ef4444;">--</h2>
                <p style="font-size:12px">Current Token: <b id="serving-token">--</b></p>
            </div>
            
            <button onclick="location.reload()" style="background:transparent; color:#6b7280; border:none; margin-top:10px;">Tap to Refresh</button>
        </div>
    </div>

    <script>
        let savedToken = localStorage.getItem('demo_token');
        let savedName = localStorage.getItem('demo_name');
        let savedSession = localStorage.getItem('demo_session');

        async function fetchStatus() {
            try {
                let res = await fetch('/status');
                let data = await res.json();
                
                // AUTO RESET CHECK
                if (savedSession && savedSession !== data.session_id) {
                    alert("System Reset by Doctor. Please book again.");
                    localStorage.clear();
                    location.reload();
                    return;
                }

                document.getElementById('live-token-display').innerText = data.current_serving;
                document.getElementById('serving-token').innerText = data.current_serving;

                if (savedToken) {
                    showStatus(savedToken, savedName, data.current_serving);
                }
            } catch(e) {}
        }

        function showStatus(token, name, current) {
            document.getElementById('booking-view').style.display = 'none';
            document.getElementById('status-view').style.display = 'block';
            document.getElementById('user-name').innerText = name;
            document.getElementById('my-token').innerText = token;
            
            let ahead = token - current;
            let badge = document.getElementById('status-badge');
            
            if (ahead > 0) {
                document.getElementById('people-ahead').innerText = ahead;
                document.getElementById('people-ahead').style.color = "#ef4444";
                badge.className = "status-badge waiting"; badge.innerText = "WAITING";
            } else if (ahead == 0) {
                document.getElementById('people-ahead').innerText = "It's your turn!";
                document.getElementById('people-ahead').style.color = "#10b981";
                badge.className = "status-badge serving"; badge.innerText = "YOUR TURN";
                if(navigator.vibrate) navigator.vibrate(200);
            } else {
                document.getElementById('people-ahead').innerText = "Done";
                badge.innerText = "COMPLETED";
            }
        }

        async function bookToken() {
            let name = document.getElementById('p-name').value;
            if(!name) return alert("Please enter name");

            let res = await fetch('/book', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            });
            let data = await res.json();
            
            savedToken = data.your_token;
            savedName = name;
            savedSession = data.session_id; 
            
            localStorage.setItem('demo_token', savedToken);
            localStorage.setItem('demo_name', savedName);
            localStorage.setItem('demo_session', savedSession);
            
            fetchStatus();
        }

        setInterval(fetchStatus, 2000);
        fetchStatus();
    </script>
</body>
</html>
"""

# ==========================================
#  💻 2. DOCTOR UI (With Branding)
# ==========================================
doctor_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Doctor Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: white; display: flex; height: 100vh; margin: 0; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 300px; background: #1e293b; padding: 30px; border-right: 1px solid #334155; display: flex; flex-direction: column; }
        .queue-list { list-style: none; padding: 0; overflow-y: auto; flex-grow: 1; }
        .queue-item { padding: 15px; border-bottom: 1px solid #334155; color: #94a3b8; display: flex; justify-content: space-between; }
        .queue-item.active { background: #334155; color: white; border-left: 4px solid #6366f1; }
        
        /* BRANDING */
        .brand-text { font-size: 10px; color: #6366f1; letter-spacing: 2px; margin-bottom: 20px; font-weight: bold; }

        /* Main Control */
        .main { flex-grow: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
        .token-card { background: #1e293b; padding: 50px 100px; border-radius: 30px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h2 { color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; font-size: 14px; margin-bottom: 20px;}
        .big-number { font-size: 150px; font-weight: bold; margin: 0; line-height: 1; color: #fff; }
        
        button { margin-top: 40px; padding: 20px 60px; font-size: 24px; background: #6366f1; color: white; border: none; border-radius: 50px; cursor: pointer; transition: 0.3s; box-shadow: 0 10px 20px rgba(99, 102, 241, 0.4); }
        button:hover { transform: translateY(-5px); }
        
        .reset-btn { position: absolute; bottom: 20px; right: 20px; background: transparent; border: 1px solid #ef4444; color: #ef4444; padding: 10px 20px; font-size: 14px; box-shadow: none; border-radius: 8px;}
        .reset-btn:hover { background: #ef4444; color: white; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="brand-text">MADE BY LAKSHAY WALIA</div>
        
        <h3 style="color:white; margin-top:0;">WAITING LIST</h3>
        <ul id="queue-list" class="queue-list"></ul>
    </div>

    <div class="main">
        <div class="token-card">
            <h2>Now Serving Token</h2>
            <div id="cur-token" class="big-number">--</div>
            <button onclick="nextPatient()">CALL NEXT &rarr;</button>
        </div>
    </div>
    
    <button class="reset-btn" onclick="resetSystem()">⚠️ Reset Queue System</button>

    <script>
        async function update() {
            let res = await fetch('/status_full'); 
            let data = await res.json();
            document.getElementById('cur-token').innerText = data.current_serving;
            
            let list = document.getElementById('queue-list');
            list.innerHTML = "";
            data.queue.forEach(p => {
                let li = document.createElement('li');
                li.className = "queue-item";
                if(p[0] == data.current_serving) li.classList.add('active');
                li.innerHTML = `<span>Token ${p[0]}</span> <span>${p[1]}</span>`;
                list.appendChild(li);
            });
        }

        async function nextPatient() { await fetch('/next', {method: 'POST'}); update(); }
        
        async function resetSystem() {
            if(confirm("Are you sure? This will delete all tokens.")) {
                await fetch('/reset', {method: 'POST'});
                update();
            }
        }
        setInterval(update, 2000);
        update();
    </script>
</body>
</html>
"""

# ==========================================
#  ⚙️ BACKEND LOGIC
# ==========================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS patients (token INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)")
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('current_serving', 0)")

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
    except: ip = "127.0.0.1"
    finally: s.close()
    return ip

@app.route('/')
def patient_view(): return render_template_string(patient_html)

@app.route('/admin')
def doctor_view(): return render_template_string(doctor_html)

@app.route('/status')
def status():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='current_serving'")
        val = cur.fetchone()[0]
    return jsonify({"current_serving": val, "session_id": CURRENT_SESSION_ID})

@app.route('/status_full')
def status_full():
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='current_serving'")
        val = cur.fetchone()[0]
        cur.execute("SELECT token, name FROM patients WHERE token >= ?", (val,))
        queue = cur.fetchall()
    return jsonify({"current_serving": val, "queue": queue})

@app.route('/book', methods=['POST'])
def book():
    name = request.json.get('name')
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO patients (name) VALUES (?)", (name,))
        token = cur.lastrowid
    return jsonify({"your_token": token, "session_id": CURRENT_SESSION_ID})

@app.route('/next', methods=['POST'])
def next_p():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE settings SET value = value + 1 WHERE key='current_serving'")
    return jsonify({"status": "ok"})

@app.route('/reset', methods=['POST'])
def reset():
    global CURRENT_SESSION_ID
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM patients")
        conn.execute("UPDATE settings SET value = 0 WHERE key='current_serving'")
        try: conn.execute("DELETE FROM sqlite_sequence WHERE name='patients'")
        except: pass
    
    # Change Session ID to force phones to reset
    CURRENT_SESSION_ID = str(uuid.uuid4())
    return jsonify({"status": "reset"})

if __name__ == '__main__':
    init_db()
    ip = get_ip_address()
    port = 5000
    url = f"http://{ip}:{port}"
    
    print(f"✅ SYSTEM READY | Made by LAKSHAY WALIA")
    print(f"👉 Doctor: {url}/admin")
    print(f"👉 Patient: {url}")
    
    qr = qrcode.make(url)
    qr.save("clinic_qr.png")
    webbrowser.open(f"{url}/admin")
    
    app.run(host='0.0.0.0', port=port)