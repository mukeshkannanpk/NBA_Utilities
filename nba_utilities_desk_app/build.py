"""
build.py - Automated Build Script for NBA Utilities
Builds all components and creates installer-ready directory structure
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


class Builder:
    """Automated builder for NBA Utilities"""
    
    def __init__(self):
        self.root_dir = Path.cwd()
        self.dist_dir = self.root_dir / "dist"
        self.build_dir = self.root_dir / "build"
        self.output_dir = self.root_dir / "NBA_Utilities_Package"
        
    def clean(self):
        """Clean previous builds"""
        print("\n[CLEAN] Removing previous builds...")
        
        for dir_path in [self.dist_dir, self.build_dir, self.output_dir]:
            if dir_path.exists():
                print(f"  Removing: {dir_path}")
                shutil.rmtree(dir_path, ignore_errors=True)
        
        print("[CLEAN] Complete!")
    
    def check_dependencies(self):
        """Verify all dependencies are installed"""
        print("\n[CHECK] Verifying dependencies...")
        
        # Map: pip package name -> import name
        required = {
            'PySide6': 'PySide6',
            'google-auth': 'google.auth',
            'google-auth-oauthlib': 'google_auth_oauthlib',
            'google-auth-httplib2': 'google_auth_httplib2',
            'google-api-python-client': 'googleapiclient',
            'pandas': 'pandas',
            'pikepdf': 'pikepdf',
            'appdirs': 'appdirs',
            'pyinstaller': 'PyInstaller',  # PyInstaller module name
        }
        
        missing = []
        for pkg, import_name in required.items():
            try:
                __import__(import_name)
                print(f"  ✓ {pkg}")
            except ImportError as e:
                print(f"  ✗ {pkg} - MISSING ({e})")
                missing.append(pkg)
        
        if missing:
            print(f"\n[ERROR] Missing packages: {', '.join(missing)}")
            print("Install with: pip install " + " ".join(missing))
            sys.exit(1)
        
        print("[CHECK] All dependencies found!")
    
    def verify_files(self):
        """Verify all required files exist"""
        print("\n[VERIFY] Checking required files...")
        
        required_files = [
            'home.py',
            'Glink.py',
            'merger.py',
            'config.py',
            'nba-utilities-home.html',
            'nba-drive-downloader.html',
            'nba-pdf-merger.html',
            'icon.ico',
        ]
        
        missing = []
        for filename in required_files:
            file_path = self.root_dir / filename
            if file_path.exists():
                print(f"  ✓ {filename}")
            else:
                print(f"  ✗ {filename} - MISSING")
                missing.append(filename)
        
        if missing:
            print(f"\n[ERROR] Missing files: {', '.join(missing)}")
            sys.exit(1)
        
        print("[VERIFY] All files found!")
    
    def build_with_pyinstaller(self):
        """Build using PyInstaller"""
        print("\n[BUILD] Building with PyInstaller...")
        
        spec_file = self.root_dir / "build_nba_utilities.spec"
        
        if not spec_file.exists():
            print(f"[ERROR] Spec file not found: {spec_file}")
            sys.exit(1)
        
        cmd = [
            sys.executable,
            '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            str(spec_file)
        ]
        
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("[ERROR] PyInstaller build failed!")
            print(result.stderr)
            sys.exit(1)
        
        print("[BUILD] PyInstaller build complete!")
    
    def organize_output(self):
        """Organize built files into installer-ready structure"""
        print("\n[ORGANIZE] Creating installer structure...")
        
        # Create output directory structure
        self.output_dir.mkdir(exist_ok=True)
        
        # Main executable directory
        main_dir = self.output_dir
        glink_dir = main_dir / "GLink"
        merger_dir = main_dir / "PDFMerger"
        
        glink_dir.mkdir(exist_ok=True)
        merger_dir.mkdir(exist_ok=True)
        
        # Copy files from dist
        dist_contents = self.dist_dir / "NBA_Utilities"
        
        if not dist_contents.exists():
            print(f"[ERROR] Dist directory not found: {dist_contents}")
            sys.exit(1)
        
        print("  Copying main application files...")
        for item in dist_contents.iterdir():
            if item.name == 'NBA_GLink_Extractor.exe':
                # Move GLink to subdirectory
                print(f"    → {item.name} to GLink/")
                shutil.copy2(item, glink_dir / item.name)
                # Copy dependencies
                for dep in dist_contents.iterdir():
                    if dep.suffix in ['.dll', '.pyd'] or dep.is_dir():
                        if dep.name not in ['GLink', 'PDFMerger']:
                            dest = glink_dir / dep.name
                            if not dest.exists():
                                if dep.is_dir():
                                    shutil.copytree(dep, dest)
                                else:
                                    shutil.copy2(dep, dest)
            
            elif item.name == 'NBA_PDF_Merger.exe':
                # Move Merger to subdirectory
                print(f"    → {item.name} to PDFMerger/")
                shutil.copy2(item, merger_dir / item.name)
                # Copy dependencies
                for dep in dist_contents.iterdir():
                    if dep.suffix in ['.dll', '.pyd'] or dep.is_dir():
                        if dep.name not in ['GLink', 'PDFMerger']:
                            dest = merger_dir / dep.name
                            if not dest.exists():
                                if dep.is_dir():
                                    shutil.copytree(dep, dest)
                                else:
                                    shutil.copy2(dep, dest)
            
            else:
                # Copy to main directory
                dest = main_dir / item.name
                if item.is_dir():
                    if not dest.exists():
                        print(f"    → {item.name}/ (directory)")
                        shutil.copytree(item, dest)
                else:
                    print(f"    → {item.name}")
                    shutil.copy2(item, dest)
        
        print("[ORGANIZE] Structure created!")
    
    def create_readme(self):
        """Create README file"""
        print("\n[README] Creating documentation...")
        
        readme_content = """NBA UTILITIES v1.0.0
===================

INSTALLATION
------------
1. Run NBA_Utilities.exe to start the main launcher
2. The application will create necessary directories in:
   - Windows: C:\\Users\\<YourName>\\AppData\\Local\\NBA\\NBA_Utilities
   - The Downloads folder will be used for output files

FIRST TIME SETUP (GLink Extractor)
----------------------------------
1. Launch GLink Extractor from the main menu
2. Upload your Google credentials.json file
3. Complete OAuth authentication
4. Your credentials will be securely stored for future use

FEATURES
--------
- GLink Extractor: Download files from Google Drive using links
- PDF Merger: Combine multiple PDF files with encryption support

TROUBLESHOOTING
---------------
- Check logs in: %LOCALAPPDATA%\\NBA\\NBA_Utilities\\nba_utilities.log
- For GLink issues: Ensure credentials.json is valid
- For PDF issues: Ensure pikepdf is working (check logs)

SYSTEM REQUIREMENTS
-------------------
- Windows 10/11 (64-bit)
- No additional software required

SUPPORT
-------
For issues, check the log file mentioned above.
"""
        
        readme_path = self.output_dir / "README.txt"
        readme_path.write_text(readme_content)
        
        print(f"  Created: {readme_path}")
        print("[README] Complete!")
    
    def create_license(self):
        """Create license file"""
        print("\n[LICENSE] Creating license...")
        
        license_content = """NBA UTILITIES LICENSE
====================

Copyright (c) 2025 NBA

All rights reserved.

This software is provided for internal use only.
"""
        
        license_path = self.output_dir / "LICENSE.txt"
        license_path.write_text(license_content)
        
        print(f"  Created: {license_path}")
        print("[LICENSE] Complete!")
    
    def print_summary(self):
        """Print build summary"""
        print("\n" + "="*60)
        print("BUILD COMPLETE!")
        print("="*60)
        print(f"\nOutput directory: {self.output_dir}")
        print("\nNext steps:")
        print("1. Test the application by running NBA_Utilities.exe")
        print("2. Create installer using Inno Setup or NSIS (see instructions)")
        print("3. Distribute the installer to users")
        print("\nDirectory structure:")
        print("  NBA_Utilities_Package/")
        print("    ├── NBA_Utilities.exe          (Main launcher)")
        print("    ├── GLink/")
        print("    │   └── NBA_GLink_Extractor.exe")
        print("    ├── PDFMerger/")
        print("    │   └── NBA_PDF_Merger.exe")
        print("    ├── [dependencies and resources]")
        print("    ├── README.txt")
        print("    └── LICENSE.txt")
        print("\n" + "="*60)
    
    def build(self):
        """Execute complete build process"""
        print("\n" + "="*60)
        print("NBA UTILITIES - AUTOMATED BUILD")
        print("="*60)
        
        try:
            self.clean()
            self.check_dependencies()
            self.verify_files()
            self.build_with_pyinstaller()
            self.organize_output()
            self.create_readme()
            self.create_license()
            self.print_summary()
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n[CANCELLED] Build cancelled by user")
            return False
        except Exception as e:
            print(f"\n\n[ERROR] Build failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    builder = Builder()
    success = builder.build()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()