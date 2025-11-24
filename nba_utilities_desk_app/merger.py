# merger.py - PRODUCTION READY VERSION
import os
import sys
import base64
import json
import traceback
from pathlib import Path
from PySide6 import QtCore
from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot, QObject, QUrl, QThread, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
import tempfile
import subprocess
import platform
import io
import time
from datetime import datetime

# Import configuration
from config import config
import logging

# Setup logging
logger = logging.getLogger(__name__)

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False
    logger.warning("pikepdf not available")


class MergeWorker(QThread):
    """Worker thread for PDF merging"""
    progress = Signal(int, int, str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, files_data, output_path, skip_encrypted):
        super().__init__()
        self.files_data = files_data
        self.output_path = output_path
        self.skip_encrypted = skip_encrypted
        self._is_cancelled = False
        
        logger.info(f"MergeWorker initialized: {len(files_data)} files")
    
    def cancel(self):
        """Cancel the merge operation"""
        self._is_cancelled = True
    
    def run(self):
        """Execute the merge operation"""
        try:
            if not PIKEPDF_AVAILABLE:
                self.error.emit("pikepdf library not installed")
                return
            
            result = self.merge_pdfs_pikepdf()
            self.finished.emit(json.dumps(result))
            
        except Exception as e:
            error_msg = f"Merge failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
    
    def merge_pdfs_pikepdf(self):
        """Merge PDF files using pikepdf"""
        merger = pikepdf.Pdf.new()
        successful = 0
        failed = 0
        total_pages_merged = 0
        errors = []
        total_files = len(self.files_data)
        
        try:
            for idx, file_data in enumerate(self.files_data):
                if self._is_cancelled:
                    raise Exception("Merge operation cancelled by user")
                
                filename = file_data['name']
                is_encrypted = file_data.get('isEncrypted', False)
                password = file_data.get('password', '')
                
                self.progress.emit(
                    idx + 1, 
                    total_files, 
                    f"Processing: {filename} ({idx + 1}/{total_files})"
                )
                
                try:
                    base64_data = file_data['base64Data']
                    if base64_data.startswith('data:'):
                        base64_data = base64_data.split(',', 1)[1]
                    
                    try:
                        pdf_bytes = base64.b64decode(base64_data, validate=True)
                    except Exception as b64_err:
                        raise ValueError(f"Corrupted base64 data: {str(b64_err)}")

                    if not pdf_bytes.startswith(b'%PDF'):
                        raise ValueError("Invalid PDF header")
                    
                    pdf_stream = io.BytesIO(pdf_bytes)
                    
                    if is_encrypted and self.skip_encrypted:
                        errors.append(f"{filename}: Skipped (encrypted)")
                        failed += 1
                        continue
                    
                    with pikepdf.open(pdf_stream, password=password) as pdf:
                        page_count = len(pdf.pages)
                        if page_count == 0:
                            errors.append(f"{filename}: No pages found")
                            failed += 1
                            continue
                        
                        merger.pages.extend(pdf.pages)
                        
                        successful += 1
                        total_pages_merged += page_count
                        logger.info(f"Added {page_count} pages from {filename}")

                except pikepdf.PasswordError:
                    logger.error(f"Wrong password for {filename}")
                    errors.append(f"{filename}: Wrong password")
                    failed += 1
                    continue
                except Exception as e:
                    error_detail = str(e)
                    logger.error(f"Failed to process {filename}: {error_detail}", exc_info=True)
                    errors.append(f"{filename}: {error_detail[:100]}")
                    failed += 1
            
            if total_pages_merged == 0:
                raise Exception("No valid pages to merge")
            
            self.progress.emit(total_files, total_files, "Finalizing and saving PDF...")
            
            try:
                with open(self.output_path, 'wb') as output_file:
                    merger.save(output_file)
            except Exception as write_err:
                raise Exception(f"Failed to write merged PDF: {str(write_err)}")
            
            merger.close()
            
            if not os.path.exists(self.output_path):
                raise Exception("Output file was not created")
            
            file_size = os.path.getsize(self.output_path)
            if file_size == 0:
                raise Exception("Output file is empty")
            
            logger.info(f"Merge complete: {successful} successful, {failed} failed")
            logger.info(f"Total pages: {total_pages_merged}")
            logger.info(f"Output: {self.output_path} ({file_size} bytes)")
            
            return {
                'success': True,
                'successful': successful,
                'failed': failed,
                'totalPages': total_pages_merged,
                'outputPath': self.output_path,
                'fileSize': file_size,
                'errors': errors
            }
            
        except Exception as final_err:
            logger.error(f"Fatal merge error: {final_err}", exc_info=True)
            raise
        finally:
            merger.close()


class PDFBridge(QObject):
    """Bridge for Python-JS communication"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.merge_worker = None
        self.temp_files = []
        self.last_output_path = None
        self.temp_view_files = []
        self.desired_output_filename = "merged.pdf"
    
    @Slot(str, str, bool)
    def startMerge(self, files_json, output_filename, skip_encrypted):
        """Start PDF merge operation"""
        try:
            files_data = json.loads(files_json)
            
            if not files_data:
                self.handleError("No files provided for merging")
                return
            
            # CHANGED: Use temp directory instead of downloads
            temp_path = config.get_temp_file(f"merge_{int(time.time())}_{output_filename}")
            if not str(temp_path).endswith('.pdf'):
                temp_path = Path(str(temp_path) + '.pdf')
            
            # Store the desired output filename for later
            self.desired_output_filename = output_filename if output_filename.endswith('.pdf') else f"{output_filename}.pdf"
            self.last_output_path = str(temp_path)
            
            logger.info(f"Starting merge of {len(files_data)} files")
            logger.info(f"Temporary output: {temp_path}")
            
            if self.merge_worker and self.merge_worker.isRunning():
                self.merge_worker.cancel()
                self.merge_worker.wait()
            
            self.merge_worker = MergeWorker(files_data, str(temp_path), skip_encrypted)
            self.merge_worker.progress.connect(self.handleProgress)
            self.merge_worker.finished.connect(self.handleComplete)
            self.merge_worker.error.connect(self.handleError)
            self.merge_worker.start()
            
        except Exception as e:
            error_msg = f"Failed to start merge: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.handleError(error_msg)
    
    @Slot(str, result=str)
    def checkEncryption(self, file_json):
        """Check if a PDF file is encrypted using pikepdf"""
        if not PIKEPDF_AVAILABLE:
            return json.dumps({'isEncrypted': False, 'type': 'none', 'error': 'pikepdf not installed'})
            
        try:
            file_data = json.loads(file_json)
            base64_data = file_data['base64Data']
            
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',', 1)[1]
            
            try:
                pdf_bytes = base64.b64decode(base64_data, validate=True)
            except Exception as b64_err:
                logger.error(f"Invalid base64: {b64_err}")
                return json.dumps({'isEncrypted': False, 'type': 'none', 'error': 'Invalid base64'})
            
            if not pdf_bytes or not pdf_bytes.startswith(b'%PDF'):
                logger.error("Invalid PDF header")
                return json.dumps({'isEncrypted': False, 'type': 'none', 'error': 'Invalid PDF'})
            
            pdf_stream = io.BytesIO(pdf_bytes)
            result = {}

            try:
                with pikepdf.open(pdf_stream, password='') as pdf:
                    if pdf.is_encrypted:
                        result = {'isEncrypted': False, 'type': 'owner_only'}
                        logger.info(f"Owner-only protected PDF: {file_data['name']}")
                    else:
                        result = {'isEncrypted': False, 'type': 'none'}
                        logger.info(f"Not encrypted: {file_data['name']}")
                        
            except pikepdf.PasswordError:
                result = {'isEncrypted': True, 'type': 'user_password'}
                logger.info(f"User password required: {file_data['name']}")
            except Exception as read_err:
                logger.error(f"Failed to read PDF: {read_err}", exc_info=True)
                result = {'isEncrypted': False, 'type': 'error', 'error': f'Cannot read PDF: {str(read_err)}'}
            
            return json.dumps(result)
        
        except Exception as e:
            logger.error(f"Encryption check failed: {e}", exc_info=True)
            return json.dumps({'isEncrypted': False, 'type': 'none', 'error': str(e)})
    
    @Slot(str)
    def viewPDF(self, file_json):
        """View PDF in default viewer"""
        try:
            file_data = json.loads(file_json)
            filename = file_data['name']
            base64_data = file_data['base64Data']
            
            if base64_data.startswith('data:'):
                base64_data = base64_data.split(',', 1)[1]
            
            try:
                pdf_bytes = base64.b64decode(base64_data, validate=True)
            except Exception as b64_err:
                self.handleError(f"Invalid PDF data: {b64_err}")
                return
            
            if not pdf_bytes.startswith(b'%PDF'):
                self.handleError("Invalid PDF file")
                return
            
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-'))
            temp_path = config.get_temp_file(f"view_{int(time.time())}_{safe_filename}")
            
            try:
                with open(temp_path, 'wb') as f:
                    f.write(pdf_bytes)
                    f.flush()
                    os.fsync(f.fileno())
                
                if sys.platform != 'win32':
                    os.chmod(temp_path, 0o644)
                
                self.temp_view_files.append(str(temp_path))
                
                if platform.system() == 'Windows':
                    os.startfile(str(temp_path))
                elif platform.system() == 'Darwin':
                    subprocess.run(['open', str(temp_path)])
                else:
                    subprocess.run(['xdg-open', str(temp_path)])
                
                logger.info(f"Opened PDF: {filename}")
            
            except Exception as open_err:
                self.handleError(f"Failed to open PDF: {open_err}")
        
        except Exception as e:
            self.handleError(f"Failed to view PDF: {str(e)}")
    
    @Slot(int, int, str)
    def handleProgress(self, current, total, message):
        """Handle progress updates from worker"""
        script = f"window.updateMergeProgress({current}, {total}, {json.dumps(message)});"
        if hasattr(self.parent(), 'view'):
            self.parent().view.page().runJavaScript(script)
    
    @Slot(str)
    def handleComplete(self, result_json):
        """Handle merge completion"""
        logger.info("Merge finished")
        
        script = f"window.handleMergeComplete({json.dumps(result_json)});"
        if hasattr(self.parent(), 'view'):
            self.parent().view.page().runJavaScript(script)
    
    @Slot(str)
    def handleError(self, error_msg):
        """Handle merge error"""
        logger.error(error_msg)
        
        script = f"window.handleMergeError({json.dumps(error_msg)});"
        if hasattr(self.parent(), 'view'):
            self.parent().view.page().runJavaScript(script)
    
    @Slot()
    def downloadMerged(self):
        """Download merged PDF"""
        if not self.last_output_path or not os.path.exists(self.last_output_path):
            QMessageBox.warning(None, "Error", "Merged PDF file not found")
            return
        
        try:
            # Use the stored desired filename
            default_name = self.desired_output_filename
            
            # Automatically save to Downloads with timestamp
            downloads_path = config.downloads_dir
            downloads_path.mkdir(exist_ok=True)
            
            # Add timestamp to avoid overwriting
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = default_name[:-4] if default_name.endswith('.pdf') else default_name
            final_name = f"{base_name}_{timestamp}.pdf"
            save_path = downloads_path / final_name
            
            # Copy from temp to downloads
            import shutil
            shutil.copy2(self.last_output_path, save_path)
            
            if sys.platform != 'win32':
                os.chmod(save_path, 0o644)
            
            QMessageBox.information(
                None,
                "Download Complete",
                f"Merged PDF saved to:\n{save_path}"
            )
            
            logger.info(f"PDF saved to: {save_path}")
            
            # Clean up temp file after successful download
            try:
                os.unlink(self.last_output_path)
                logger.info("Cleaned up temporary merge file")
            except:
                pass
                
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.warning(None, "Error", error_msg)
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.merge_worker and self.merge_worker.isRunning():
            self.merge_worker.cancel()
            self.merge_worker.wait()
        
        for temp_file in self.temp_view_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        self.temp_files.clear()
        self.temp_view_files.clear()


class MainWindow(QMainWindow):
    def __init__(self, html_path: str):
        super().__init__()
        self.setWindowTitle("NBA PDF Merger")
        self.setMinimumSize(1000, 750)
        self.resize(1200, 850)
        
        if config.icon_path and os.path.exists(config.icon_path):
            self.setWindowIcon(QIcon(config.icon_path))
        
        self.center_on_screen()
        
        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)
        
        self.channel = QWebChannel()
        self.bridge = PDFBridge(parent=self)
        self.channel.registerObject("pdfBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        
        self.load_html_and_inject_js(html_path)
        
        logger.info("PDF Merger window initialized")
    
    def center_on_screen(self):
        """Center window on screen"""
        try:
            screen = QApplication.primaryScreen().geometry()
            window = self.frameGeometry()
            center_point = screen.center()
            window.moveCenter(center_point)
            self.move(window.topLeft())
        except Exception as e:
            logger.warning(f"Could not center window: {e}")
    
    def load_html_and_inject_js(self, html_path):
        """Load HTML with WebChannel integration"""
        try:
            if not os.path.exists(html_path):
                raise FileNotFoundError(f"HTML file not found: {html_path}")
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            js_file = QtCore.QFile(":/qtwebchannel/qwebchannel.js")
            if not js_file.open(QtCore.QIODevice.ReadOnly):
                logger.error("Failed to load qwebchannel.js")
                return
            
            qwebchannel_js = js_file.readAll().data().decode('utf-8')
            js_file.close()
            
            bridge_script = f"""
            <script type="text/javascript">
            {qwebchannel_js}
            </script>
            <script type="text/javascript">
            window.bridgeReady = false;
            window.isDesktopMode = true;
            window.pdfBridge = null;
            
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('[BRIDGE] Initializing WebChannel...');
                
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.pdfBridge = channel.objects.pdfBridge;
                    window.bridgeReady = true;
                    
                    console.log('[BRIDGE] Bridge connected successfully');
                    
                    if (typeof window.onBridgeReady === 'function') {{
                        window.onBridgeReady();
                    }}
                }});
            }});
            </script>
            """
            
            if "</head>" in html_content:
                html_content = html_content.replace("</head>", f"{bridge_script}</head>", 1)
            else:
                html_content += bridge_script
            
            base_url = QUrl.fromLocalFile(os.path.dirname(os.path.abspath(html_path)) + "/")
            self.view.setHtml(html_content, base_url)
            
            logger.info("HTML loaded with WebChannel bridge")
            
        except Exception as e:
            error_msg = f"Error loading HTML: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.view.setHtml(f"<h1>Error</h1><p>{error_msg}</p>")
    
    def closeEvent(self, event):
        """Handle window close"""
        logger.info("PDF Merger closing...")
        
        if hasattr(self, 'bridge'):
            self.bridge.cleanup()
        
        if hasattr(self, 'view'):
            try:
                self.view.page().deleteLater()
                self.view.deleteLater()
            except:
                pass
        
        event.accept()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("NBA PDF Merger")
    app.setOrganizationName("NBA")
    
    logger.info("=" * 70)
    logger.info("NBA PDF MERGER - STARTING")
    if PIKEPDF_AVAILABLE:
        logger.info(f"pikepdf version: {pikepdf.__version__}")
    else:
        logger.warning("pikepdf NOT AVAILABLE")
    logger.info("=" * 70)
    
    if not PIKEPDF_AVAILABLE:
        QMessageBox.critical(
            None,
            "Missing Dependency",
            "pikepdf library is not installed.\n\n"
            "Please install it with:\npip install pikepdf"
        )
        sys.exit(1)
    
    html_path = config.merger_html
    
    if not os.path.exists(html_path):
        QMessageBox.critical(
            None,
            "Error",
            f"Could not find HTML file:\n{html_path}\n\n"
            "Please reinstall the application."
        )
        sys.exit(1)
    
    window = MainWindow(str(html_path))
    window.show()
    
    logger.info("PDF Merger started successfully")
    
    exit_code = app.exec()
    logger.info("PDF Merger exiting")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()