// ── YT_Downloader Frontend ──

const socket = io();

// Elements
const urlInput       = document.getElementById('urlInput');
const clearUrl       = document.getElementById('clearUrl');
const outputPath     = document.getElementById('outputPath');
const browseBtn      = document.getElementById('browseBtn');
const dirPicker      = document.getElementById('dirPicker');
const downloadBtn    = document.getElementById('downloadBtn');
const progressSection= document.getElementById('progressSection');
const progressFill   = document.getElementById('progressFill');
const progressGlow   = document.getElementById('progressGlow');
const progressPct    = document.getElementById('progressPct');
const progressLabel  = document.getElementById('progressLabel');
const progressSpeed  = document.getElementById('progressSpeed');
const progressEta    = document.getElementById('progressEta');
const logsToggle     = document.getElementById('logsToggle');
const toggleArrow    = document.getElementById('toggleArrow');
const logsSection    = document.getElementById('logsSection');
const logsBody       = document.getElementById('logsBody');
const clearLogsBtn   = document.getElementById('clearLogs');
const logBadge       = document.getElementById('logBadge');
const statusDot      = document.getElementById('statusDot');
const statusText     = document.getElementById('statusText');
const videoInfo      = document.getElementById('videoInfo');
const viTitle        = document.getElementById('viTitle');
const viUploader     = document.getElementById('viUploader');
const viDuration     = document.getElementById('viDuration');
const successToast   = document.getElementById('successToast');
const toastText      = document.getElementById('toastText');

let logCount = 0;
let logsOpen = false;
let isDownloading = false;

// ── Status ──
function setStatus(state, text) {
  statusDot.className = 'status-dot ' + state;
  statusText.textContent = text;
}

// ── Logs ──
function appendLog(msg, level = 'info') {
  const line = document.createElement('span');
  line.className = 'log-line ' + level;

  // Auto-classify log lines by content
  if (level === 'info' && msg.includes('[download]')) level = 'download';
  line.className = 'log-line ' + level;

  const ts = new Date().toTimeString().slice(0,8);
  line.textContent = `[${ts}] ${msg}`;
  logsBody.appendChild(line);
  logsBody.appendChild(document.createElement('br'));
  logsBody.scrollTop = logsBody.scrollHeight;

  logCount++;
  if (!logsOpen) {
    logBadge.style.display = 'inline-block';
    logBadge.textContent = logCount;
  }
}

function openLogs() {
  logsOpen = true;
  logsSection.classList.add('open');
  toggleArrow.classList.add('open');
  logsToggle.querySelector('span:nth-child(2)').textContent = 'Hide Logs';
  logBadge.style.display = 'none';
  logCount = 0;
}

function closeLogs() {
  logsOpen = false;
  logsSection.classList.remove('open');
  toggleArrow.classList.remove('open');
  logsToggle.querySelector('span:nth-child(2)').textContent = 'Show Logs';
}

logsToggle.addEventListener('click', () => {
  if (logsOpen) closeLogs();
  else openLogs();
});

clearLogsBtn.addEventListener('click', () => {
  logsBody.innerHTML = '';
  logCount = 0;
  logBadge.style.display = 'none';
});

// ── Clear URL ──
clearUrl.addEventListener('click', () => {
  urlInput.value = '';
  urlInput.focus();
});

// ── Browse ──
browseBtn.addEventListener('click', () => dirPicker.click());

dirPicker.addEventListener('change', (e) => {
  const files = e.target.files;
  if (files && files.length > 0) {
    // Extract directory path from first file
    const fullPath = files[0].webkitRelativePath || files[0].name;
    const parts = fullPath.split('/');
    // We only have the folder name from the browser — set as placeholder
    const dirName = parts[0];
    outputPath.value = dirName;
    appendLog(`[info] Output folder selected: ${dirName}`, 'info');
  }
});

// ── Progress ──
function showProgress(pct) {
  progressSection.style.display = 'block';
  progressFill.style.width = pct + '%';
  progressPct.textContent = pct + '%';

  if (pct >= 100) {
    progressGlow.style.opacity = '0';
    progressFill.style.background = 'var(--green)';
    progressLabel.textContent = 'Complete';
  } else {
    progressGlow.style.opacity = '1';
    progressFill.style.background = 'var(--red)';
  }
}

function resetProgress() {
  progressFill.style.width = '0%';
  progressFill.style.background = 'var(--red)';
  progressPct.textContent = '0%';
  progressLabel.textContent = 'Downloading…';
  progressSpeed.textContent = '—';
  progressEta.textContent = 'ETA —';
  progressGlow.style.opacity = '1';
}

// ── Video info ──
function showVideoInfo(data) {
  viTitle.textContent = data.title || '—';
  viUploader.textContent = data.uploader || '—';
  const dur = data.duration;
  if (dur) {
    const m = Math.floor(dur / 60), s = dur % 60;
    viDuration.textContent = `${m}:${s.toString().padStart(2,'0')}`;
  } else {
    viDuration.textContent = '—';
  }
  videoInfo.style.display = 'block';
}

// ── Toast ──
function showToast(msg, isSuccess = true) {
  const icon = successToast.querySelector('.toast-icon');
  icon.textContent = isSuccess ? '✓' : '✕';
  icon.style.color = isSuccess ? 'var(--green)' : 'var(--red)';
  toastText.textContent = msg;
  successToast.classList.add('show');
  setTimeout(() => successToast.classList.remove('show'), 3500);
}

// ── Download ──
function startDownload() {
  const url = urlInput.value.trim();
  const path = outputPath.value.trim();

  if (!url) {
    urlInput.focus();
    appendLog('[error] Please enter a YouTube URL.', 'error');
    openLogs();
    return;
  }

  if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
    appendLog('[warning] URL may not be a valid YouTube link.', 'warning');
  }

  isDownloading = true;
  downloadBtn.disabled = true;
  downloadBtn.querySelector('.btn-text').textContent = 'Downloading…';
  downloadBtn.querySelector('.btn-icon').textContent = '⏳';

  videoInfo.style.display = 'none';
  resetProgress();
  showProgress(0);
  setStatus('active', 'Downloading…');

  socket.emit('start_download', { url, output_path: path });
}

downloadBtn.addEventListener('click', startDownload);

urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') startDownload();
});

// ── Socket Events ──
socket.on('connect', () => {
  setStatus('ready', 'Connected');
  appendLog('[socket] Connected to server.', 'debug');
});

socket.on('disconnect', () => {
  setStatus('error', 'Disconnected');
  appendLog('[socket] Connection lost.', 'warning');
});

socket.on('connected', (data) => {
  if (data.default_path && !outputPath.value) {
    outputPath.placeholder = data.default_path;
  }
});

socket.on('video_info', (data) => {
  showVideoInfo(data);
});

socket.on('progress', (data) => {
  const pct = data.percent || 0;
  showProgress(pct);

  if (data.speed) progressSpeed.textContent = data.speed;
  if (data.eta)   progressEta.textContent = `ETA ${data.eta}`;
  if (data.log)   appendLog(data.log, 'download');
});

socket.on('log', (data) => {
  appendLog(data.message || '', data.level || 'info');
});

socket.on('done', (data) => {
  isDownloading = false;
  downloadBtn.disabled = false;
  downloadBtn.querySelector('.btn-text').textContent = 'Download';
  downloadBtn.querySelector('.btn-icon').textContent = '↓';

  if (data.success) {
    setStatus('success', 'Complete');
    showProgress(100);
    showToast('Download complete!', true);
    appendLog('[✓] Download finished successfully!', 'success');
  } else {
    setStatus('error', 'Failed');
    appendLog('[✕] Download failed: ' + data.message, 'error');
    openLogs();
    alert('Error occurred\n\nSee logs for details.');
  }
});
