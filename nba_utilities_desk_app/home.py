"""
home.py - NBA Utilities Main Application (Production)
Robust main launcher with proper error handling and resource management
"""
import os
import sys
import subprocess
import signal
import atexit
import logging
from pathlib import Path
from PySide6 import QtCore, QtGui
from PySide6.QtCore import Slot, QObject, QUrl, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# Import configuration
from config import config

# Setup logging
log_file = config.user_data_dir / "nba_utilities.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Bridge(QObject):
    """Enhanced bridge with robust process management"""
    
    error_occurred = QtCore.Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.child_processes = []
        self.launching = False
        self.launch_timeout = 10000  # 10 seconds
        
        atexit.register(self.cleanup_processes)
        
        # Setup signal handlers for Unix-like systems
        if sys.platform != 'win32':
            try:
                signal.signal(signal.SIGCHLD, self._handle_sigchld)
                logger.info("SIGCHLD handler registered")
            except Exception as e:
                logger.warning(f"Could not register SIGCHLD handler: {e}")
    
    def _handle_sigchld(self, signum, frame):
        """Reap zombie processes on Unix-like systems"""
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                logger.info(f"Reaped zombie process PID: {pid}")
                self.child_processes = [p for p in self.child_processes 
                                       if p.poll() is not None or p.pid != pid]
            except ChildProcessError:
                break
            except Exception as e:
                logger.warning(f"SIGCHLD handler error: {e}")
                break
    
    @Slot(str)
    def navigateTo(self, tool: str):
        """Launch tool with comprehensive error handling"""
        if self.launching:
            QMessageBox.information(None, "Please Wait", 
                                   "Another tool is launching. Please wait...")
            return
        
        self.launching = True
        
        # Show loading message
        loading_msg = QMessageBox(
            QMessageBox.Information,
            "Launching",
            f"Starting {tool.upper()} tool...\nPlease wait...",
            QMessageBox.NoButton
        )
        loading_msg.setWindowModality(QtCore.Qt.NonModal)
        loading_msg.show()
        QApplication.processEvents()
        
        try:
            if tool == "glink":
                self._launch_glink(loading_msg)
            elif tool == "pdf":
                self._launch_pdf(loading_msg)
            else:
                loading_msg.close()
                QMessageBox.warning(None, "Unknown Tool", 
                                   f"Tool '{tool}' is not recognized.")
        except Exception as e:
            loading_msg.close()
            error_msg = f"Failed to launch {tool}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(None, "Launch Error", error_msg)
            self.error_occurred.emit(error_msg)
        finally:
            self.launching = False
    
    def _launch_glink(self, loading_msg):
        """Launch GLink Extractor"""
        logger.info("Launching GLink Extractor...")
        
        # Check if already running
        if any(p.poll() is None for p in self.child_processes 
               if hasattr(p, '_tool_name') and p._tool_name == 'glink'):
            loading_msg.close()
            logger.warning("GLink Extractor already running")
            QMessageBox.information(None, "Already Running", 
                                   "GLink Extractor is already running.")
            return
        
        # Determine command
        if config.is_frozen and config.glink_exe.exists():
            cmd = [str(config.glink_exe)]
            logger.info(f"Using bundled executable: {config.glink_exe}")
        elif config.glink_exe.exists() and config.glink_exe.suffix == '.py':
            cmd = [sys.executable, str(config.glink_exe)]
            logger.info(f"Using Python script: {config.glink_exe}")
        else:
            raise FileNotFoundError(f"GLink executable not found: {config.glink_exe}")
        
        # Launch process
        process = self._launch_process(cmd, "GLink Extractor")
        process._tool_name = 'glink'
        self.child_processes.append(process)
        
        # Verify launch
        QTimer.singleShot(500, lambda: self._verify_launch(
            loading_msg, "GLink Extractor", process))
    
    def _launch_pdf(self, loading_msg):
        """Launch PDF Merger"""
        logger.info("Launching PDF Merger...")
        
        # Check if already running
        if any(p.poll() is None for p in self.child_processes 
               if hasattr(p, '_tool_name') and p._tool_name == 'pdf'):
            loading_msg.close()
            logger.warning("PDF Merger already running")
            QMessageBox.information(None, "Already Running", 
                                   "PDF Merger is already running.")
            return
        
        # Determine command
        if config.is_frozen and config.merger_exe.exists():
            cmd = [str(config.merger_exe)]
            logger.info(f"Using bundled executable: {config.merger_exe}")
        elif config.merger_exe.exists() and config.merger_exe.suffix == '.py':
            cmd = [sys.executable, str(config.merger_exe)]
            logger.info(f"Using Python script: {config.merger_exe}")
        else:
            raise FileNotFoundError(f"PDF Merger executable not found: {config.merger_exe}")
        
        # Launch process
        process = self._launch_process(cmd, "PDF Merger")
        process._tool_name = 'pdf'
        self.child_processes.append(process)
        
        # Verify launch
        QTimer.singleShot(500, lambda: self._verify_launch(
            loading_msg, "PDF Merger", process))
    
    def _launch_process(self, cmd, tool_name):
        """Launch subprocess with proper flags"""
        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        
        try:
            process = subprocess.Popen(
                cmd,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(config.exe_dir) if config.is_frozen else None
            )
            logger.info(f"{tool_name} launched with PID: {process.pid}")
            return process
        except Exception as e:
            logger.error(f"Failed to launch {tool_name}: {e}", exc_info=True)
            raise
    
    def _verify_launch(self, loading_msg, tool_name, process):
        """Verify tool launched successfully"""
        loading_msg.close()
        
        if process.poll() is None:
            QMessageBox.information(None, "Success", 
                                   f"{tool_name} launched successfully!")
        else:
            returncode = process.poll()
            error_msg = f"{tool_name} exited unexpectedly (code: {returncode})"
            logger.error(error_msg)
            QMessageBox.warning(None, "Launch Issue", 
                              f"{error_msg}\n\nCheck logs at:\n{log_file}")
            self.error_occurred.emit(error_msg)
    
    def cleanup_processes(self):
        """Terminate all child processes gracefully"""
        logger.info("Cleaning up child processes...")
        
        for process in self.child_processes:
            if process and process.poll() is None:
                try:
                    tool_name = getattr(process, '_tool_name', 'Unknown')
                    logger.info(f"Terminating {tool_name} (PID {process.pid})...")
                    
                    if sys.platform == 'win32':
                        process.terminate()
                    else:
                        process.send_signal(signal.SIGTERM)
                    
                    try:
                        process.wait(timeout=3)
                        logger.info(f"Process {process.pid} terminated gracefully")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Forcing kill on PID {process.pid}...")
                        process.kill()
                        process.wait()
                        logger.info(f"Process {process.pid} killed")
                except Exception as e:
                    logger.warning(f"Error terminating process: {e}")
                    try:
                        process.kill()
                    except:
                        pass
        
        self.child_processes.clear()
        logger.info("Cleanup complete")


class MainWindow(QMainWindow):
    """Enhanced main window with better error handling"""
    
    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_webview()
        self._load_content()
        
        logger.info("Main window initialized")
    
    def _setup_window(self):
        """Setup window properties"""
        self.setWindowTitle(f"NBA Utilities v{config.VERSION}")
        self.setMinimumSize(980, 720)
        self.resize(1100, 780)
        
        # Set icon if available
        if config.icon_path and os.path.exists(config.icon_path):
            self.setWindowIcon(QtGui.QIcon(config.icon_path))
        
        self._center_on_screen()
    
    def _center_on_screen(self):
        """Center window on screen"""
        try:
            screen_geometry = QApplication.primaryScreen().geometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
        except Exception as e:
            logger.warning(f"Could not center window: {e}")
    
    def _setup_webview(self):
        """Setup web view with bridge"""
        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)
        
        # Setup WebChannel
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("pybridge", self.bridge)
        self.view.page().setWebChannel(self.channel)
        
        # Connect error signal
        self.bridge.error_occurred.connect(self._handle_bridge_error)
    
    def _handle_bridge_error(self, error_msg):
        """Handle errors from bridge"""
        logger.error(f"Bridge error: {error_msg}")
    
    def _load_content(self):
        """Load HTML content with bridge injection"""
        try:
            html_path = config.home_html
            
            if not os.path.exists(html_path):
                raise FileNotFoundError(f"HTML file not found: {html_path}")
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Get WebChannel JavaScript
            js_file = QtCore.QFile(":/qtwebchannel/qwebchannel.js")
            if not js_file.open(QtCore.QIODevice.ReadOnly):
                raise Exception("Failed to load qwebchannel.js")
            
            qwebchannel_js = js_file.readAll().data().decode('utf-8')
            js_file.close()
            
            # Inject bridge script
            bridge_script = f"""
            <script type="text/javascript">
            {qwebchannel_js}
            </script>
            <script type="text/javascript">
            window.bridgeReady = false;
            
            function callBridgeSafely(method, ...args) {{
                if (window.bridgeReady && typeof method === 'function') {{
                    return method(...args);
                }} else {{
                    console.error('Bridge not ready');
                    alert('Application is still loading. Please wait...');
                    return Promise.reject('Bridge not ready');
                }}
            }}
            
            document.addEventListener('DOMContentLoaded', function() {{
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    window.pybridge = channel.objects.pybridge;
                    window.bridgeReady = true;
                    console.log('[BRIDGE] Connected successfully');
                }});
            }});
            
            window.navigateTo = function(tool) {{
                callBridgeSafely(window.pybridge.navigateTo, tool);
            }};
            </script>
            """
            
            if "</head>" in html_content:
                html_content = html_content.replace("</head>", f"{bridge_script}</head>", 1)
            else:
                html_content += bridge_script
            
            base_url = QUrl.fromLocalFile(os.path.dirname(html_path) + "/")
            self.view.setHtml(html_content, base_url)
            
            logger.info("HTML content loaded successfully")
            
        except Exception as e:
            error_msg = f"Error loading HTML: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.view.setHtml(f"<h1>Error</h1><p>{error_msg}</p><p>Check logs at: {log_file}</p>")
    
    def closeEvent(self, event):
        """Handle window close"""
        logger.info("Main window closing...")
        
        # Clean up web view
        if hasattr(self, 'view'):
            try:
                self.view.page().deleteLater()
                self.view.deleteLater()
            except:
                pass
        
        # Check for running processes
        active_processes = [p for p in self.bridge.child_processes 
                          if p and p.poll() is None]
        
        if active_processes:
            reply = QMessageBox.question(
                self,
                'Confirm Exit',
                f'There are {len(active_processes)} tool(s) still running.\n'
                'Closing will terminate all tools.\n\nExit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        # Cleanup
        self.bridge.cleanup_processes()
        config.cleanup_temp()
        
        event.accept()
        logger.info("Application closed")


def main():
    """Main application entry point"""
    try:
        # Setup Qt application
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        app = QApplication(sys.argv)
        app.setApplicationName("NBA Utilities")
        app.setOrganizationName("NBA")
        app.setApplicationVersion(config.VERSION)
        
        logger.info("=" * 60)
        logger.info(f"NBA UTILITIES v{config.VERSION} - STARTING")
        logger.info(f"Running as: {'Frozen Executable' if config.is_frozen else 'Python Script'}")
        logger.info(f"Base Path: {config.base_path}")
        logger.info(f"User Data: {config.user_data_dir}")
        logger.info(f"Log File: {log_file}")
        logger.info("=" * 60)
        
        # Verify critical resources
        if not os.path.exists(config.home_html):
            QMessageBox.critical(
                None,
                "Missing Resource",
                f"Critical file missing: {config.home_html}\n\n"
                "Please reinstall the application."
            )
            sys.exit(1)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Application started successfully")
        
        # Run application
        exit_code = app.exec()
        
        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"Application failed to start:\n{str(e)}\n\n"
            f"Check logs at:\n{log_file}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()