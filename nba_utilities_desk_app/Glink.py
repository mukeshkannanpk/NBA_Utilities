# -*- coding: utf-8 -*-
# Glink.py - PRODUCTION READY VERSION
import os
import sys
import re
import ssl
import time
import json
import shutil
import tempfile
import zipfile
import threading
import concurrent.futures
import pandas as pd
from datetime import datetime
from collections import deque
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PySide6.QtCore import Slot, QObject, QUrl, Signal, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6 import QtCore
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import stat

# Import configuration
from config import config
import logging

# Setup logging
logger = logging.getLogger(__name__)

# ===========================
# CONFIG
# ===========================
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_PATH = str(config.glink_token)
CREDENTIALS_PATH = str(config.glink_credentials)

# ===========================
# DOWNLOAD WORKER THREAD
# ===========================
class DownloadWorker(QThread):
    """Worker thread for downloading files"""
    progress_update = Signal(int, int)
    download_complete = Signal(str)
    error = Signal(str)
    
    def __init__(self, df, selected_cols, credentials, settings):
        super().__init__()
        self.df = df
        self.selected_cols = selected_cols
        self.credentials = credentials
        self.settings = settings
        
        # Use config downloads directory
        downloads_dir = config.downloads_dir
        downloads_dir.mkdir(exist_ok=True)
        self.temp_dir = tempfile.mkdtemp(dir=str(downloads_dir), prefix="glink_")
        
        self.is_cancelled = False
        self.success_files = []
        self.failed_rows = []
        
        # Rate limiting
        self.request_times = deque(maxlen=10)
        self.rate_limit_lock = threading.Lock()
        
        logger.info(f"Worker temp directory: {self.temp_dir}")
        
    def extract_file_id(self, url):
        """Extract Google Drive file ID from URL"""
        if pd.isna(url) or not isinstance(url, str):
            return None
        url = url.strip()
        
        patterns = [
            r'id=([^&]+)',
            r'/file/d/([a-zA-Z0-9-_]+)',
            r'/open\?id=([a-zA-Z0-9-_]+)',
            r'd/([a-zA-Z0-9-_]+)',
            r'/document/d/([a-zA-Z0-9-_]+)',
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'/presentation/d/([a-zA-Z0-9-_]+)',
            r'/u/\d+/file/d/([a-zA-Z0-9-_]+)',
            r'file/d/([a-zA-Z0-9-_]+)/preview',
            r'file/d/([a-zA-Z0-9-_]+)/view',
        ]
        
        for pattern in patterns:
            m = re.search(pattern, url)
            if m:
                file_id = m.group(1)
                if len(file_id) > 10 and re.match(r'^[a-zA-Z0-9-_]+$', file_id):
                    return file_id
        
        return None
    
    def safe_filename(self, name):
        """Remove invalid characters from filename"""
        name = re.sub(r'[<>:"/\\|?*]', '_', str(name))
        name = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', name)
        if len(name) > 200:
            name = name[:200]
        return name
    
    def rate_limit_wait(self):
        """Enforce rate limiting"""
        with self.rate_limit_lock:
            now = time.time()
            if len(self.request_times) >= 10:
                oldest = self.request_times[0]
                elapsed = now - oldest
                if elapsed < 1.0:
                    sleep_time = 1.0 - elapsed
                    logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            self.request_times.append(time.time())
    
    def download_single_file(self, index, row):
        """Download a single file from Google Drive"""
        if self.is_cancelled:
            return {"index": index, "error": "Cancelled"}
        
        self.rate_limit_wait()
        
        try:
            creds = self._get_fresh_credentials()
            drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
            
            file_id = self.extract_file_id(row["Glink"])
            if not file_id:
                return {"index": index, "error": "Invalid link"}
            
            parts = [self.safe_filename(str(row[c])) for c in self.selected_cols if c in row and pd.notna(row[c])]
            base_name = "_".join(parts) if parts else f"file_{index}"
            
            try:
                meta = drive_service.files().get(fileId=file_id, fields="name,mimeType,size").execute()
                original_name = meta.get("name", "")
                ext = os.path.splitext(original_name)[1] or ".file"
                mime_type = meta.get("mimeType", "")
                
                if "google-apps" in mime_type:
                    ext = ".pdf"
                    logger.info(f"Google Workspace file: {original_name}")
                    
            except HttpError as e:
                if e.resp.status == 404:
                    return {"index": index, "error": "File not found (404)"}
                elif e.resp.status == 403:
                    return {"index": index, "error": "Access denied (403)"}
                else:
                    ext = ".file"
                    logger.warning(f"Metadata error: {e}")
            
            target_path = os.path.join(self.temp_dir, f"{base_name}{ext}")
            
            counter = 1
            while os.path.exists(target_path):
                target_path = os.path.join(self.temp_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            
            chunk_size = self.settings['chunk'] * 1024 * 1024
            retries = self.settings['retries']
            
            for attempt in range(1, retries + 1):
                if self.is_cancelled:
                    return {"index": index, "error": "Cancelled"}
                
                try:
                    if "google-apps" in mime_type:
                        req = drive_service.files().export_media(fileId=file_id, mimeType='application/pdf')
                    else:
                        req = drive_service.files().get_media(fileId=file_id)
                    
                    with open(target_path, "wb") as fh:
                        downloader = MediaIoBaseDownload(fh, req, chunksize=chunk_size)
                        done = False
                        while not done and not self.is_cancelled:
                            status, done = downloader.next_chunk()
                            if status and int(status.progress() * 100) % 25 == 0:
                                logger.debug(f"{base_name}: {int(status.progress() * 100)}%")
                    
                    if self.is_cancelled:
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        return {"index": index, "error": "Cancelled"}
                    
                    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                        logger.info(f"Downloaded: {base_name}{ext}")
                        return {"path": target_path, "name": os.path.basename(target_path)}
                    else:
                        raise Exception("Downloaded file is empty")
                    
                except (ssl.SSLError, HttpError, ConnectionError, OSError) as e:
                    if attempt < retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Retry {attempt}/{retries} for {base_name} in {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        error_msg = str(e)
                        if isinstance(e, HttpError):
                            if e.resp.status == 403:
                                error_msg = "Access denied - quota exceeded"
                            elif e.resp.status == 404:
                                error_msg = "File not found"
                            elif e.resp.status == 500:
                                error_msg = "Google Drive server error"
                        logger.error(f"{base_name} - {error_msg}")
                        return {"index": index, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Downloading row {index}: {str(e)}", exc_info=True)
            return {"index": index, "error": str(e)}
    
    def _get_fresh_credentials(self):
        """Get credentials and refresh if expired"""
        creds = Credentials(
            token=self.credentials.token,
            refresh_token=self.credentials.refresh_token,
            token_uri=self.credentials.token_uri,
            client_id=self.credentials.client_id,
            client_secret=self.credentials.client_secret,
            scopes=self.credentials.scopes
        )
        
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed token")
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
        
        return creds
    
    def run(self):
        """Main worker thread execution"""
        try:
            total = len(self.df)
            completed = 0
            
            logger.info(f"Downloading {total} files with {self.settings['threads']} threads")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.settings['threads']) as executor:
                futures = [executor.submit(self.download_single_file, i, row) 
                          for i, row in self.df.iterrows()]
                
                for fut in concurrent.futures.as_completed(futures):
                    if self.is_cancelled:
                        logger.info("Download cancelled by user")
                        for f in futures:
                            f.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    try:
                        res = fut.result(timeout=5)
                    except concurrent.futures.TimeoutError:
                        res = {"index": -1, "error": "Timeout"}
                    except Exception as e:
                        res = {"index": -1, "error": str(e)}
                    
                    completed += 1
                    self.progress_update.emit(completed, total)
                    
                    if res.get("path"):
                        self.success_files.append((res["path"], res["name"]))
                    else:
                        self.failed_rows.append({
                            "index": res.get("index", -1), 
                            "error": res.get("error", "Unknown")
                        })
            
            if self.success_files and not self.is_cancelled:
                logger.info(f"Creating ZIP with {len(self.success_files)} files")
                zip_path = os.path.join(self.temp_dir, "downloads.zip")
                
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for path, name in self.success_files:
                        if os.path.exists(path):
                            zipf.write(path, arcname=name)
                
                results = {
                    "successful": len(self.success_files),
                    "failed": len(self.failed_rows),
                    "errors": self.failed_rows,
                    "zipPath": zip_path
                }
                
                logger.info(f"Download complete: {results['successful']} successful, {results['failed']} failed")
                self.download_complete.emit(json.dumps(results))
                
            elif self.is_cancelled:
                self.error.emit("Download cancelled")
            else:
                self.error.emit("No files downloaded")
                
        except Exception as e:
            logger.error(f"Worker error: {str(e)}", exc_info=True)
            self.error.emit(f"Download failed: {str(e)}")
        finally:
            time.sleep(1)
            self.cleanup()
    
    def cancel(self):
        """Cancel download"""
        self.is_cancelled = True
        logger.info("Stopping downloads")
        self.requestInterruption()
    
    def cleanup(self):
        """Clean up temp directory"""
        try:
            if os.path.exists(self.temp_dir):
                time.sleep(1)
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info("Cleaned up temp files")
        except Exception as e:
            logger.warning(f"Cleanup error: {str(e)}")
    
    def __del__(self):
        """Destructor"""
        self.cleanup()


# ===========================
# BRIDGE CLASS
# ===========================
class DriveDownloaderBridge(QObject):
    """Bridge between JavaScript and Python"""
    
    authSuccess = Signal()
    authPending = Signal()
    authError = Signal()
    fileLoaded = Signal(str)
    progressUpdate = Signal(int, int)
    downloadComplete = Signal(str)
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.credentials = None
        self.df = None
        self.worker = None
        self.zip_path = None
        self.last_temp_dir = None
        
        # Ensure user data directory exists
        config.user_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"User data directory: {config.user_data_dir}")
        
    @Slot()
    def checkAuthentication(self):
        """Check for existing credentials"""
        logger.info("Checking credentials")
        
        try:
            if os.path.exists(TOKEN_PATH):
                logger.info("Found token.json")
                self.authPending.emit()
                self.authenticate()
            elif os.path.exists(CREDENTIALS_PATH):
                logger.info("Found credentials.json")
                self.authPending.emit()
                self.authenticate()
            else:
                logger.info("No credentials found")
                self.authError.emit()
        except Exception as e:
            logger.error(f"Auth check error: {str(e)}", exc_info=True)
            self.authError.emit()
    
    @Slot()
    def uploadCredentials(self):
        """Upload credentials.json"""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select credentials.json",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    creds_data = json.load(f)
                
                if "installed" not in creds_data and "web" not in creds_data:
                    raise ValueError("Invalid credentials format")
                
                if os.path.exists(CREDENTIALS_PATH):
                    os.remove(CREDENTIALS_PATH)
                
                shutil.copy(file_path, CREDENTIALS_PATH)
                
                # Set proper permissions
                if sys.platform != 'win32':
                    os.chmod(CREDENTIALS_PATH, 0o600)
                
                logger.info(f"Credentials saved to: {CREDENTIALS_PATH}")
                self.authPending.emit()
                self.authenticate()
            except json.JSONDecodeError:
                error_msg = "Invalid JSON file"
                logger.error(error_msg)
                self.error.emit(error_msg)
                self.authError.emit()
            except Exception as e:
                error_msg = f"Failed to load credentials: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.error.emit(error_msg)
                self.authError.emit()
    
    def authenticate(self):
        """Authenticate with Google Drive"""
        try:
            creds = None
            
            if os.path.exists(TOKEN_PATH):
                try:
                    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
                    logger.info("Loaded token.json")
                except Exception as e:
                    logger.warning(f"Token load failed: {e}")
                    if os.path.exists(TOKEN_PATH):
                        os.remove(TOKEN_PATH)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing token")
                        creds.refresh(Request())
                        logger.info("Token refreshed")
                        
                        with open(TOKEN_PATH, "w") as token:
                            token.write(creds.to_json())
                        logger.info("Saved refreshed token")
                    except Exception as e:
                        logger.error(f"Refresh failed: {e}")
                        creds = None
                
                if not creds:
                    if not os.path.exists(CREDENTIALS_PATH):
                        error_msg = "Please upload credentials.json first"
                        logger.error(error_msg)
                        self.error.emit(error_msg)
                        self.authError.emit()
                        return
                    
                    logger.info("Starting OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    with open(TOKEN_PATH, "w") as token:
                        token.write(creds.to_json())
                    logger.info("Saved token.json")
            
            self.credentials = creds
            self.authSuccess.emit()
            logger.info("Authentication successful")
            
        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            self.authError.emit()
    
    @Slot()
    def uploadDataFile(self):
        """Upload Excel/CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Select Excel or CSV file",
            "",
            "Spreadsheet Files (*.csv *.xlsx *.xls)"
        )
        
        if file_path:
            try:
                logger.info(f"Loading file: {file_path}")
                
                if file_path.endswith('.csv'):
                    self.df = pd.read_csv(file_path, encoding='utf-8')
                else:
                    self.df = pd.read_excel(file_path)
                
                if "Glink" not in self.df.columns:
                    error_msg = "Column 'Glink' not found"
                    logger.error(error_msg)
                    self.error.emit(error_msg)
                    self.df = None
                    return
                
                original_count = len(self.df)
                self.df = self.df.dropna(subset=['Glink'])
                removed_count = original_count - len(self.df)
                
                if removed_count > 0:
                    logger.info(f"Removed {removed_count} empty rows")
                
                if len(self.df) == 0:
                    error_msg = "No valid data rows"
                    logger.error(error_msg)
                    self.error.emit(error_msg)
                    self.df = None
                    return
                
                file_data = {
                    "rowCount": len(self.df),
                    "columns": [c for c in self.df.columns if c != "Glink"],
                    "fileName": os.path.basename(file_path)
                }
                self.fileLoaded.emit(json.dumps(file_data))
                logger.info(f"Loaded {len(self.df)} records")
                
            except Exception as e:
                error_msg = f"Failed to load file: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.error.emit(error_msg)
                self.df = None
    
    @Slot(str, result=str)
    def startDownload(self, settings_json):
        """Start download process"""
        if not self.credentials:
            error_msg = "Please authenticate first"
            logger.error(error_msg)
            self.error.emit(error_msg)
            return json.dumps({"success": False})
        
        if self.df is None or len(self.df) == 0:
            error_msg = "Please upload a data file"
            logger.error(error_msg)
            self.error.emit(error_msg)
            return json.dumps({"success": False})
        
        try:
            settings = json.loads(settings_json)
            selected_cols = settings['columns']
            
            if not selected_cols:
                error_msg = "Select at least one column"
                logger.error(error_msg)
                self.error.emit(error_msg)
                return json.dumps({"success": False})
            
            logger.info(f"Settings: {settings['threads']} threads, {settings['chunk']}MB chunks")
            
            if self.worker and self.worker.isRunning():
                logger.warning("Previous download running")
                self.worker.cancel()
                self.worker.wait(5000)
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait()
            
            self.worker = DownloadWorker(
                self.df.copy(),
                selected_cols,
                self.credentials,
                settings
            )
            
            self.worker.progress_update.connect(self.on_progress_update)
            self.worker.download_complete.connect(self.on_download_complete)
            self.worker.error.connect(self.on_error)
            self.worker.start()
            
            logger.info("Download started")
            return json.dumps({"success": True})
            
        except Exception as e:
            error_msg = f"Failed to start: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            return json.dumps({"success": False})
    
    @Slot()
    def cancelDownload(self):
        """Cancel download"""
        if self.worker and self.worker.isRunning():
            logger.info("Cancelling download")
            self.worker.cancel()
    
    def on_progress_update(self, completed, total):
        """Forward progress"""
        self.progressUpdate.emit(completed, total)
    
    def on_download_complete(self, results_json):
        """Handle completion"""
        try:
            results = json.loads(results_json)
            self.zip_path = results.get('zipPath')
            self.last_temp_dir = self.worker.temp_dir if self.worker else None
            
            if self.zip_path and os.path.exists(self.zip_path):
                default_name = f"drive_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                save_path = config.downloads_dir / default_name
                
                try:
                    shutil.copy(self.zip_path, save_path)
                    
                    if sys.platform != 'win32':
                        os.chmod(save_path, 0o644)
                    
                    if self.last_temp_dir and os.path.exists(self.last_temp_dir):
                        shutil.rmtree(self.last_temp_dir, ignore_errors=True)
                    
                    QMessageBox.information(
                        None,
                        "Download Complete",
                        f"Successfully downloaded {results['successful']} files!\n\n"
                        f"Saved to: {save_path}\n"
                        f"Failed: {results['failed']} files"
                    )
                    
                    logger.info(f"ZIP saved to: {save_path}")
                    self.downloadComplete.emit(results_json)
                    
                except Exception as e:
                    error_msg = f"Failed to save ZIP: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    QMessageBox.critical(None, "Error", error_msg)
                    self.error.emit(error_msg)
            else:
                self.downloadComplete.emit(results_json)
                
        except Exception as e:
            error_msg = f"Error processing completion: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
    
    def on_error(self, error_msg):
        """Forward error"""
        self.error.emit(error_msg)
    
    @Slot()
    def downloadZip(self):
        """Re-download ZIP"""
        if not self.zip_path or not os.path.exists(self.zip_path):
            QMessageBox.warning(None, "Error", "No download available")
            return
        
        default_name = f"drive_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        save_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save ZIP File",
            default_name,
            "ZIP Files (*.zip)"
        )
        
        if save_path:
            try:
                shutil.copy(self.zip_path, save_path)
                QMessageBox.information(None, "Success", f"ZIP saved to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(None, "Error", f"Failed to save: {str(e)}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()


# ===========================
# MAIN WINDOW
# ===========================
class DriveDownloaderWindow(QMainWindow):
    """Main window for Drive Downloader"""
    
    def __init__(self, html_content):
        super().__init__()
        self.setWindowTitle("NBA GLink Extractor")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Set icon if available
        if config.icon_path and os.path.exists(config.icon_path):
            self.setWindowIcon(QIcon(config.icon_path))
        
        self.center_on_screen()
        
        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)
        
        self.channel = QWebChannel()
        self.bridge = DriveDownloaderBridge()
        self.channel.registerObject("driveBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        
        self.bridge.authSuccess.connect(lambda: self.call_js("window.onAuthSuccess()"))
        self.bridge.authPending.connect(lambda: self.call_js("window.onAuthPending()"))
        self.bridge.authError.connect(lambda: self.call_js("window.onAuthError()"))
        self.bridge.fileLoaded.connect(self.on_file_loaded)
        self.bridge.progressUpdate.connect(lambda c, t: self.call_js(f"window.onProgressUpdate({c}, {t})"))
        self.bridge.downloadComplete.connect(self.on_download_complete_js)
        self.bridge.error.connect(self.on_error_js)
        
        self.load_html_with_bridge(html_content)
        logger.info("Window initialized")
    
    def center_on_screen(self):
        """Center window"""
        try:
            screen = QApplication.primaryScreen().geometry()
            window = self.frameGeometry()
            window.moveCenter(screen.center())
            self.move(window.topLeft())
        except Exception as e:
            logger.warning(f"Could not center window: {e}")
    
    def call_js(self, script):
        """Execute JavaScript"""
        self.view.page().runJavaScript(script)
    
    def escape_js_string(self, s):
        """Escape string for JavaScript"""
        return (s.replace('\\', '\\\\')
                 .replace("'", "\\'")
                 .replace('"', '\\"')
                 .replace('\n', '\\n')
                 .replace('\r', '\\r')
                 .replace('\t', '\\t'))
    
    def on_file_loaded(self, data):
        """Handle file loaded"""
        escaped = self.escape_js_string(data)
        self.call_js(f"window.onFileLoaded('{escaped}')")
    
    def on_download_complete_js(self, data):
        """Handle download complete"""
        escaped = self.escape_js_string(data)
        self.call_js(f"window.onDownloadComplete('{escaped}')")
    
    def on_error_js(self, msg):
        """Handle error"""
        escaped = self.escape_js_string(msg)
        self.call_js(f"window.onError('{escaped}')")
    
    def load_html_with_bridge(self, html_content):
        """Load HTML with bridge"""
        js_file = QtCore.QFile(":/qtwebchannel/qwebchannel.js")
        if not js_file.open(QtCore.QIODevice.ReadOnly):
            logger.error("Failed to load qwebchannel.js")
            return
        
        qwebchannel_js = js_file.readAll().data().decode('utf-8')
        js_file.close()
        
        bridge_script = f"""
        <script>
        {qwebchannel_js}
        </script>
        <script>
        window.driveBridge = null;
        window.bridgeReady = false;
        
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            window.driveBridge = channel.objects.driveBridge;
            window.bridgeReady = true;
            console.log('[BRIDGE] Connected');
            
            if (window.driveBridge.checkAuthentication) {{
                window.driveBridge.checkAuthentication();
            }}
        }});
        </script>
        """
        
        if "</head>" in html_content:
            html_content = html_content.replace("</head>", f"{bridge_script}</head>")
        
        self.view.setHtml(html_content, QUrl("file:///"))
        logger.info("HTML loaded")
    
    def closeEvent(self, event):
        """Handle window close"""
        logger.info("GLink Extractor closing")
        
        if self.bridge.worker and self.bridge.worker.isRunning():
            reply = QMessageBox.question(
                self,
                'Download in Progress',
                'Download in progress. Cancel and exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            logger.info("Cancelling download")
            self.bridge.worker.cancel()
            self.bridge.worker.wait(5000)
            if self.bridge.worker.isRunning():
                self.bridge.worker.terminate()
        
        self.bridge.cleanup()
        
        if hasattr(self, 'view'):
            try:
                self.view.page().deleteLater()
                self.view.deleteLater()
            except:
                pass
        
        event.accept()
        logger.info("Closed cleanly")


# ===========================
# MAIN APPLICATION
# ===========================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NBA GLink Extractor")
    app.setOrganizationName("NBA")
    
    logger.info("=" * 60)
    logger.info("NBA GLINK EXTRACTOR - STARTING")
    logger.info(f"Credentials: {CREDENTIALS_PATH}")
    logger.info(f"Token: {TOKEN_PATH}")
    logger.info("=" * 60)
    
    # Use config HTML path
    html_path = config.glink_html
    
    if not os.path.exists(html_path):
        QMessageBox.critical(
            None,
            "Missing File",
            f"Could not find HTML file:\n{html_path}\n\n"
            "Please reinstall the application."
        )
        sys.exit(1)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    window = DriveDownloaderWindow(html_content)
    window.show()
    
    logger.info("GLink Extractor started successfully")
    
    exit_code = app.exec()
    logger.info("GLink Extractor exiting")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()