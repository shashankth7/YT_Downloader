import os
import threading

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR   = os.path.join(BASE_DIR, 'frontend', 'static')
COOKIES_DIR   = os.path.join(BASE_DIR, 'backend', 'cookies')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config['SECRET_KEY'] = 'yt_downloader_secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

download_state = {'running': False, 'sid': None}


def emit_safe(event, data, sid):
    socketio.emit(event, data, to=sid)


def progress_hook(d):
    sid = download_state.get('sid')
    if not sid:
        return

    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        speed = d.get('speed', 0) or 0
        eta   = d.get('eta', 0) or 0
        percent = (downloaded / total * 100) if total else 0
        speed_str = f"{speed/1024/1024:.2f} MB/s" if speed else "N/A"
        eta_str   = f"{int(eta)}s" if eta else "N/A"
        filename  = os.path.basename(d.get('filename', ''))
        log_msg   = f"[download] {percent:.1f}% at {speed_str} ETA {eta_str}"
        emit_safe('progress', {
            'percent': round(percent, 1),
            'speed': speed_str, 'eta': eta_str,
            'filename': filename, 'log': log_msg
        }, sid)

    elif d['status'] == 'finished':
        filename = os.path.basename(d.get('filename', ''))
        emit_safe('progress', {
            'percent': 100,
            'log': f"[download] Finished: {filename}",
            'finished_file': filename
        }, sid)

    elif d['status'] == 'error':
        emit_safe('log', {'message': '[error] Download error', 'level': 'error'}, sid)


def run_download(url, output_path, sid):
    try:
        import yt_dlp
        download_state['running'] = True
        download_state['sid'] = sid

        emit_safe('log', {'message': f'[info] Starting download...', 'level': 'info'}, sid)
        emit_safe('log', {'message': f'[info] URL: {url}', 'level': 'info'}, sid)
        emit_safe('log', {'message': f'[info] Output: {output_path}', 'level': 'info'}, sid)

        os.makedirs(output_path, exist_ok=True)

        class LogCapture:
            def debug(self, msg):
                if not msg.startswith('[debug]'):
                    emit_safe('log', {'message': msg, 'level': 'debug'}, sid)
            def warning(self, msg):
                emit_safe('log', {'message': f'[warning] {msg}', 'level': 'warning'}, sid)
            def error(self, msg):
                emit_safe('log', {'message': f'[error] {msg}', 'level': 'error'}, sid)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'logger': LogCapture(),
        }
        # If a cookiefile path was provided via download_state, use it
        cookiefile = download_state.get('cookiefile')
        if cookiefile:
            if os.path.exists(cookiefile):
                ydl_opts['cookiefile'] = cookiefile
                emit_safe('log', {'message': f'[info] Using cookiefile: {cookiefile}', 'level': 'info'}, sid)
            else:
                emit_safe('log', {'message': f'[warning] Cookiefile not found: {cookiefile}', 'level': 'warning'}, sid)
        emit_safe('log', {'message': '[info] Fetching video info...', 'level': 'info'}, sid)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title    = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            emit_safe('log', {'message': f'[info] Title: {title}', 'level': 'info'}, sid)
            emit_safe('log', {'message': f'[info] Uploader: {uploader}', 'level': 'info'}, sid)
            emit_safe('log', {'message': f'[info] Duration: {duration}s', 'level': 'info'}, sid)
            emit_safe('video_info', {'title': title, 'uploader': uploader, 'duration': duration}, sid)
            ydl.download([url])

        emit_safe('log', {'message': '[info] ✓ Download completed!', 'level': 'success'}, sid)
        emit_safe('done', {'success': True, 'message': 'Download completed!'}, sid)

    except Exception as e:
        emit_safe('log', {'message': f'[error] {str(e)}', 'level': 'error'}, sid)
        emit_safe('done', {'success': False, 'message': str(e)}, sid)
    finally:
        download_state['running'] = False
        download_state['sid'] = None
        # clear cookiefile from shared state after run
        download_state['cookiefile'] = None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_cookies', methods=['POST'])
def upload_cookies():
    if 'cookies' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    f = request.files['cookies']
    if f.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(f.filename)
    os.makedirs(COOKIES_DIR, exist_ok=True)
    path = os.path.join(COOKIES_DIR, filename)
    f.save(path)
    return jsonify({'path': path, 'filename': filename})


@app.route('/list_dir', methods=['GET'])
def list_dir():
    # Return a JSON list of directories for a given path (server-side browsing)
    req_path = request.args.get('path')
    if not req_path:
        req_path = os.path.expanduser('~')

    # Normalize and ensure path exists
    req_path = os.path.abspath(os.path.expanduser(req_path))
    if not os.path.exists(req_path):
        return jsonify({'error': 'Path not found'}), 404

    entries = []
    try:
        for name in sorted(os.listdir(req_path)):
            full = os.path.join(req_path, name)
            if os.path.isdir(full):
                entries.append({'name': name, 'path': full})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    parent = os.path.dirname(req_path) if req_path != '/' else None
    return jsonify({'path': req_path, 'parent': parent, 'dirs': entries})


@app.route('/make_dir', methods=['POST'])
def make_dir():
    data = request.get_json() or {}
    parent = data.get('parent')
    name = data.get('name')
    if not parent or not name:
        return jsonify({'error': 'parent and name required'}), 400

    parent = os.path.abspath(os.path.expanduser(parent))
    new_path = os.path.join(parent, secure_filename(name))
    try:
        os.makedirs(new_path, exist_ok=True)
        return jsonify({'path': new_path, 'name': os.path.basename(new_path)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@socketio.on('start_download')
def handle_download(data):
    url         = data.get('url', '').strip()
    output_path = data.get('output_path', '').strip()
    sid         = request.sid
    cookiefile   = data.get('cookiefile')

    if not url:
        emit('done', {'success': False, 'message': 'Please enter a YouTube URL.'})
        return

    if not output_path:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads')

    if download_state['running']:
        emit('done', {'success': False, 'message': 'A download is already in progress.'})
        return

    # Attach cookiefile path into shared state for the download thread
    download_state['cookiefile'] = cookiefile

    thread = threading.Thread(target=run_download, args=(url, output_path, sid), daemon=True)
    thread.start()


@socketio.on('connect')
def handle_connect():
    default_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    emit('connected', {'default_path': default_path})


if __name__ == '__main__':
    print("\n🚀 Starting YT_Downloader...")
    print("📡 Server running at http://127.0.0.1:5001")
    print("✅ Ready for downloads!\n")
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
