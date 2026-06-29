# YT_Downloader 🎥

A simple and clean web application to download YouTube videos with real-time progress tracking and logging.

---

## 🚀 Features

- 🎬 Download YouTube videos in best quality (bestvideo+bestaudio → MP4)
- 📊 Real-time progress bar with speed and ETA
- 📋 Live log streaming via WebSockets
- 🗂 Custom output directory selection
- ⚠️ Error handling with auto-open logs on failure
- 🌑 Dark terminal-style UI

---

## 🏗️ Project Structure

```
YT_Downloader/
├── backend/
│   └── app.py              # Flask + SocketIO server
├── frontend/
│   ├── templates/
│   │   └── index.html      # Main UI
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
├── requirements.txt
└── README.md
```

---

## ⚙️ Requirements

* Python 3.8+
* pip

---

## 📦 Installation

1. Clone the repository:

```bash
git clone https://github.com/shashankth7/YT_Downloader.git
cd YT_Downloader
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

> **Note:** `ffmpeg` must be installed for merging video+audio streams.
> - macOS: `brew install ffmpeg`
> - Ubuntu: `sudo apt install ffmpeg`
> - Windows: Download from https://ffmpeg.org/download.html

---

## ▶️ Running the Application

1. Start the backend server:

```bash
python backend/app.py
```

2. Open your browser and go to:

```
http://127.0.0.1:5001
```

---

## 🧠 How It Works

* User enters a YouTube link.
* Selects output path.
* Clicks download.
* Backend uses **yt-dlp** to download the video.
* Progress updates are sent to frontend.
* Logs are displayed in real-time.
* If any error occurs:

  * Popup message shown
  * Logs auto-expand

---

## 📌 Example Code (yt-dlp)

```python
import yt_dlp

url = "https://www.youtube.com/watch?v=mn5cjXbitwo"

ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': '/desired/path/%(title)s.%(ext)s',
    'merge_output_format': 'mp4',
    'noplaylist': True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
```

---

## Tech Stack

| Layer    | Technology              |
|----------|-------------------------|
| Backend  | Python, Flask           |
| Sockets  | Flask-SocketIO, Threading|
| Download | yt-dlp                  |
| Frontend | Vanilla JS, CSS3        |
| Fonts    | JetBrains Mono, Inter   |


## 🛠️ Future Improvements

* Add video quality selection
* Support playlists
* Add authentication
* Save download history

---

## ⚠️ Disclaimer

This tool is for educational purposes only. Please ensure you comply with YouTube's terms of service before downloading content.

---

## 👨‍💻 Author

Shashank Thakur
