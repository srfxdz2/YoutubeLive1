from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import subprocess
import threading
import os
import random , requests
import time
import os
import subprocess
import requests
import time
from dotenv import load_dotenv
import os
#from downloader import download

#download()

# Load the .env file
load_dotenv()

# Access environment variables
ngrok_token = os.getenv("ngrok_token")
telegram_token = os.getenv("telegram_token")

def run_command(command, shell=False):
    """Runs a shell command and prints output."""
    try:
        result = subprocess.run(command, shell=shell, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(e.stderr)
        return None

def is_package_installed(package_name):
    """Check if a package is installed."""
    try:
        result = subprocess.run(["dpkg", "-l", package_name], check=True, text=True, capture_output=True)
        return package_name in result.stdout
    except subprocess.CalledProcessError:
        return False

def is_ngrok_installed():
    """Check if ngrok is installed."""
    try:
        result = subprocess.run(["ngrok", "version"], check=True, text=True, capture_output=True)
        return "ngrok" in result.stdout
    except FileNotFoundError:
        return False

def send_telegram_message(message, bot_token, chat_id):
    """Send a message to a Telegram bot."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
        else:
            print(f"Failed to send Telegram message. Response: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# Telegram bot details
bot_token = telegram_token
chat_id = "7132001605"



# Step 2: Check and install ngrok
if is_ngrok_installed():
    print("ngrok is already installed. Skipping installation.")
else:
    print("Downloading ngrok...")
    run_command(["wget", "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"])
    
    print("Extracting ngrok...")
    run_command(["tar", "-xvzf", "ngrok-v3-stable-linux-amd64.tgz"])
    
    print("Moving ngrok to /usr/local/bin...")
    run_command(["mv", "ngrok", "/usr/local/bin/"])

    print("Adding ngrok auth token...")
    auth_token = ngrok_token
    run_command(["ngrok", "config", "add-authtoken", auth_token])

# Step 3: Run ngrok and send the URL
print("Starting ngrok on port 5000...")
ngrok_process = subprocess.Popen(["ngrok", "http", "5000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Wait a few seconds for ngrok to initialize
time.sleep(5)

# Get ngrok URL from API
try:
    response = requests.get("http://localhost:4040/api/tunnels")
    if response.status_code == 200:
        tunnels = response.json().get("tunnels", [])
        if tunnels:
            public_url = tunnels[0].get("public_url", "No URL found")
            print(f"ngrok public URL: {public_url}")
            send_telegram_message(f"ngrok public URL: {public_url}", bot_token, chat_id)
        else:
            print("No tunnels found.")
    else:
        print(f"Failed to retrieve ngrok tunnels. Response: {response.text}")
except Exception as e:
    print(f"Error retrieving ngrok URL: {e}")








app = Flask(__name__)
app.secret_key = 'srfxdz'

video_folder = 'yt_music'
video_files = [f for f in os.listdir(video_folder) if f.endswith(('.mp4', '.avi', '.mov'))]

stream_url = 'rtmp://a.rtmp.youtube.com/live2'
streaming_process = None
def is_streaming():
    """Check if the streaming process is running."""
    global streaming_process
    return streaming_process is not None and streaming_process.poll() is None


def init_db():
    conn = sqlite3.connect('stream.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS stream_key (id INTEGER PRIMARY KEY, key TEXT)''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        key = request.form.get('key')
        if key == 'srfxdz':
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid Key!", 403
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('authenticated'):
        return redirect(url_for('login'))

    conn = sqlite3.connect('stream.db')
    cursor = conn.cursor()

    # Fetch the current stream key
    cursor.execute('SELECT key FROM stream_key WHERE id=1')
    data = cursor.fetchone()
    saved_stream_key = data[0] if data else ''

    # Fetch all saved keys
    cursor.execute('SELECT key FROM stream_key')
    all_keys = [row[0] for row in cursor.fetchall()]
    conn.close()

    if request.method == 'POST':
        stream_key = request.form.get('stream_key')
        conn = sqlite3.connect('stream.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stream_key WHERE id=1')
        cursor.execute('INSERT INTO stream_key (id, key) VALUES (1, ?)', (stream_key,))
        conn.commit()
        conn.close()
        saved_stream_key = stream_key  # Update the displayed key
        return redirect(url_for('dashboard'))

    return render_template(
        'dashboard.html',
        stream_key=saved_stream_key,
        all_keys=all_keys,
        streaming=is_streaming()  # Check if the stream is running
    )

def stream_video():
    global streaming_process
    while True:
        video_path = os.path.join(video_folder, random.choice(video_files))

        conn = sqlite3.connect('stream.db')
        cursor = conn.cursor()
        cursor.execute('SELECT key FROM stream_key WHERE id=1')
        data = cursor.fetchone()
        conn.close()

        if not data:
            print("Stream key not set.")
            break

        stream_key = data[0]

        ffmpeg_command = [
            'ffmpeg',
            '-re',  # Real-time streaming (forces reading from the file in real-time)
            '-i', video_path,  # Input video path
            '-vcodec', 'libx264',  # Video codec (H.264)
            '-acodec', 'aac',  # Audio codec (AAC)
            '-b:v', '6000k',  # Video bitrate (8 Mbps)
            '-r', '60',  # Frame rate (60 fps)
            '-preset', 'ultrafast',  # Fast encoding speed for minimal CPU usage (you can adjust to 'veryfast' or 'superfast' if needed)
            '-crf', '25',  # Constant Rate Factor (lower value = better quality, higher CPU usage)
            '-maxrate', '6000k',  # Maximum video bitrate
            '-bufsize', '12000k',  # Buffer size for bitrate control
            '-threads', '0',  # Use all available CPU threads
            '-f', 'flv',  # Output format (FLV for streaming)
            f'{stream_url}/{stream_key}'  # Stream URL with stream key
        ]


        # Start the streaming process
        streaming_process = subprocess.Popen(ffmpeg_command)
        streaming_process.wait()

@app.route('/start', methods=['POST'])
def start_stream():

    os.system("sudo apt update && sudo apt upgrade -y")
    os.system("sudo apt install ffmpeg -y")
    global streaming_process
    if not is_streaming():
        thread = threading.Thread(target=stream_video, daemon=True)
        thread.start()
    return redirect(url_for('dashboard'))


@app.route('/stop', methods=['POST'])
def stop_stream():
    global streaming_process
    if streaming_process is not None:
        streaming_process.terminate()
        #streaming_process.wait()  # Ensure the process is stopped
        streaming_process = None
    return redirect(url_for('dashboard'))





if __name__ == '__main__':
    init_db()

    # # Get the local IP address
    # import socket
    # local_ip = socket.gethostbyname(socket.gethostname())
    port = 5000

    # # Construct and send the message
    # message = f"Flask app started. Access it at http://{local_ip}:{port}"
    # send_telegram_message(message)

    # # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=True)


