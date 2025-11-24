"""
config.py - Centralized Configuration for NBA Utilities
Handles paths, settings, and environment detection for production deployment
"""
import os
import sys
from pathlib import Path
import appdirs


class AppConfig:
    """Application configuration with proper path handling"""
    
    APP_NAME = "NBA_Utilities"
    APP_AUTHOR = "NBA"
    VERSION = "1.0.0"
    
    def __init__(self):
        self._setup_paths()
    
    def _setup_paths(self):
        """Setup all application paths based on environment"""
        
        # Detect if running as PyInstaller bundle
        self.is_frozen = getattr(sys, 'frozen', False)
        
        if self.is_frozen:
            # Running as compiled executable
            self.base_path = sys._MEIPASS
            self.exe_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            self.exe_dir = self.base_path
        
        # User data directory (for credentials, tokens, etc.)
        # Uses platform-specific locations:
        # Windows: C:\Users\<user>\AppData\Local\NBA\NBA_Utilities
        # macOS: ~/Library/Application Support/NBA_Utilities
        # Linux: ~/.local/share/NBA_Utilities
        self.user_data_dir = Path(appdirs.user_data_dir(self.APP_NAME, self.APP_AUTHOR))
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Downloads directory
        self.downloads_dir = Path.home() / "Downloads"
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Temp directory for processing
        self.temp_dir = Path(appdirs.user_cache_dir(self.APP_NAME, self.APP_AUTHOR))
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # HTML files (bundled with app)
        self.home_html = self._get_resource_path("nba-utilities-home.html")
        self.glink_html = self._get_resource_path("nba-drive-downloader.html")
        self.merger_html = self._get_resource_path("nba-pdf-merger.html")
        
        # Icon file
        self.icon_path = self._get_resource_path("icon.ico")
        
        # GLink specific paths (stored in user data)
        self.glink_credentials = self.user_data_dir / "credentials.json"
        self.glink_token = self.user_data_dir / "token.json"
        
        # Sub-executable paths (for child processes)
        if self.is_frozen:
            # When frozen, sub-apps are in subdirectories
            self.glink_exe = Path(self.exe_dir) / "GLink" / "NBA_GLink_Extractor.exe"
            self.merger_exe = Path(self.exe_dir) / "PDFMerger" / "NBA_PDF_Merger.exe"
        else:
            # When running as script, use Python files
            self.glink_exe = Path(self.base_path) / "Glink.py"
            self.merger_exe = Path(self.base_path) / "merger.py"
    
    def _get_resource_path(self, relative_path):
        """Get absolute path to bundled resource"""
        return os.path.join(self.base_path, relative_path)
    
    def get_temp_file(self, filename):
        """Get path for temporary file"""
        return self.temp_dir / filename
    
    def cleanup_temp(self):
        """Clean up temporary files"""
        import shutil
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"[WARN] Could not clean temp directory: {e}")


# Global config instance
config = AppConfig()