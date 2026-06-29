import os
import threading

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR   = os.path.join(BASE_DIR, 'frontend', 'static')

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


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('start_download')
def handle_download(data):
    url         = data.get('url', '').strip()
    output_path = data.get('output_path', '').strip()
    sid         = request.sid

    if not url:
        emit('done', {'success': False, 'message': 'Please enter a YouTube URL.'})
        return

    if not output_path:
        output_path = os.path.join(os.path.expanduser('~'), 'Downloads')

    if download_state['running']:
        emit('done', {'success': False, 'message': 'A download is already in progress.'})
        return

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
