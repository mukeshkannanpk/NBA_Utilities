#  📃⚡NBA Utilities  
### Automated Google Drive Downloader & Unlimited Offline PDF Merger

A powerful, cross-platform desktop application built to **automate NBA (Training & Placement) documentation** by eliminating manual Google Drive downloads and offering a **free, unlimited, offline PDF merging utility**—all in one application.
<img width="1919" height="1021" alt="image" src="https://github.com/user-attachments/assets/be3cf167-901c-48ee-8402-845447f83f9c" />
<img width="1919" height="1024" alt="image" src="https://github.com/user-attachments/assets/b96a8ad9-5ab0-4482-bdb2-243cbe073cd1" />
<img width="1918" height="1019" alt="image" src="https://github.com/user-attachments/assets/7dfe9719-8ca7-42c4-963f-bc27045a0cef" />


---

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Why This Project Matters](#why-this-project-matters)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Application Modules](#application-modules)
- [Folder Structure](#folder-structure)
- [Installation (Developer Guide)](#installation-developer-guide)
- [Building EXE + Installer](#building-exe--installer)
- [License](#license)

---

## Overview

During an internship with the **Training and Placement Cell**, our team encountered a massive bottleneck in the NBA documentation process:

- Over **1500+ PDFs** had to be manually downloaded from Google Drive links listed in Google Sheets.
- This required days of repeated clicking, organizing, and naming.
- Online PDF mergers had file-size or file-count restrictions.
- Sensitive student data couldn’t be uploaded to online tools due to privacy concerns.

### 🎯 Solution  
**NBA Utilities** combines two major automation tools:

1. **GLink Extractor** – Automates bulk Google Drive downloads from Google Sheet links.  
2. **Offline PDF Merger** – Merges thousands of PDFs into one file securely on the local machine.

<b>No limits. No subscriptions. No data leaks.<b>

---

## Key Features

### 🚀 Operational Efficiency
- Automates fetching and downloading **1500+ PDF files** in a single click.
- Multi-threaded parallel downloading.
- Auto-folder creation and file organization.

### 💸 Cost Saving
- 100% free offline PDF merging.
- No online services or paid subscriptions needed.

### 🔐 Security & Reliability
- Fully offline PDF merging (protects sensitive student data).
- Automatically detects and skips encrypted PDFs and logs them.

### 🖥 Modern UI
- Built using **PySide6 + QtWebEngine**.
- Responsive HTML/CSS frontend integrated with Python backend.

### 📦 Production-Ready Deployment
- Fully standalone `.exe` file built using **PyInstaller**.
- Professional Windows installer built using **Inno Setup**.

---

## Why This Project Matters

| Problem | Solution |
|--------|----------|
| Manual downloads take days | Automated parallel Drive downloader |
| Online mergers have limits | Unlimited offline PDF merging |
| Sensitive data risk | Fully offline operation |
| Team workload wasted | Frees team to focus on validation instead of downloading |

---

## Architecture & Tech Stack

### Core Technologies
| Component | Technology |
|----------|------------|
| Backend | Python 3.9+ |
| GUI | PySide6, QtWebEngine |
| PDF Processing | pikepdf |
| Google Drive API | google-auth, googleapiclient |
| Config & Paths | appdirs, config.py |
| Packaging | PyInstaller |
| Installer | Inno Setup |

---

## Application Modules

### `home.py`
- Main launcher and UI handler.
- Manages subprocesses for GLink.exe and Merger.exe.
- Centralized logging and error handling.

### `Glink.py`
- Google OAuth 2.0 authentication.
- Extracts file URLs from Google Sheets.
- Multi-threaded high-speed PDF downloading.

### `merger.py`
- Merges thousands of PDFs using pikepdf.
- Worker threads for smooth UI experience.
- Skips encrypted PDFs and writes logs.

### `config.py`
- Handles app directory paths using `appdirs`.
- Detects PyInstaller runtime (`sys._MEIPASS`).

### `installer.iss`
- Complete Inno Setup configuration for generating Windows installer.

---

## Folder Structure
```arduino
NBA_Utilities/
│
├── home.py
├── Glink.py
├── merger.py
├── config.py
├── build.py
├── nba-drive-downloader.html
├── nba-pdf-merger.html
├── nba-utilities-home.html
├── credentials.json
├── icon.ico  
├── installer.iss
├── build_nba_utilities.spec
├── requirements.txt 
└── README.md
```

## Installation (Developer Guide)

### 1. Clone the Repository
```bash
git clone https://github.com/YourUsername/NBA-Utilities.git
cd NBA_Utilities
```
### 2. Create & Activate Virtual Environment
```bash
python -m venv .venv
# Activate manually depending on OS
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Add Google API Credentials
Place your credentials.json in the /resources/ folder.

## Building EXE & Installer
### 1. Run the Build Script
```bash
python build.py
```

This generates:

- All .exe files

- NBA_Utilities_Package/ directory

### 2. Build Installer via Inno Setup

- Open Inno Setup Compiler

- Load installer/installer.iss

- Compile

### Output:

Installer/NBA_Utilities_Setup_vX.X.X.exe

## License

- This project is licensed under the MIT License.
- See the LICENSE file for details.
