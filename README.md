# 📃⚡ Placement Cell Document Automation Suite

> **A production-ready desktop application that automates bulk Google Drive document retrieval and provides secure, unlimited offline PDF merging.**

Built using **Python**, **PySide6**, **Qt WebEngine**, **HTML/CSS/JavaScript**, and the **Google Drive API** to eliminate repetitive documentation work inside the Training & Placement Cell.

---

## 📸 Application Preview

<p align="center">
<img width="100%" src="https://github.com/user-attachments/assets/be3cf167-901c-48ee-8402-845447f83f9c">

<br><br>

<img width="100%" src="https://github.com/user-attachments/assets/b96a8ad9-5ab0-4482-bdb2-243cbe073cd1">

<br><br>

<img width="100%" src="https://github.com/user-attachments/assets/7dfe9719-8ca7-42c4-963f-bc27045a0cef">
</p>

---

# 🚀 Project Overview

During my internship at the **Training and Placement Cell, Bannari Amman Institute of Technology**, I observed that a significant amount of time was spent performing repetitive document management tasks.

The team frequently had to:

- Download **1500+ student PDFs** individually from Google Drive links stored in spreadsheets.
- Rename and organize files manually.
- Merge hundreds of PDFs using online services with strict upload limits.
- Handle confidential student documents that could not be uploaded to third-party websites.

These manual activities consumed several hours every placement cycle.

To solve this problem, I designed and developed a complete desktop automation solution from scratch.

---

# 💡 Solution

The application consists of two integrated productivity tools.

## 📥 GLink Extractor

Automates bulk downloading of Google Drive documents directly from Excel or CSV files.

### Features

- Google OAuth 2.0 Authentication
- Bulk Google Drive Downloads
- Multi-threaded Download Engine
- Automatic Retry Mechanism
- Progress Tracking
- ZIP Packaging
- Automatic File Naming
- Google Docs Export Support
- Parallel Downloads
- Download Cancellation

---

## 📄 Offline PDF Merger

A completely offline PDF processing utility.

### Features

- Unlimited PDF Merge
- Password Detection
- Skip Encrypted PDFs
- Progress Reporting
- Local Processing
- No Upload Limits
- No Internet Required

---

# 📈 Impact

The application significantly reduced manual effort during placement documentation.

| Before | After |
|---------|--------|
| Manual download of 1500+ files | Automated bulk download |
| Several hours of repetitive work | Completed in minutes |
| Online PDF merger limitations | Unlimited offline merging |
| Sensitive documents uploaded online | Entire workflow remains local |

---

# 🏗 Architecture

```
                        NBA Utilities

                     Desktop Launcher
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
  Google Drive Downloader             PDF Merger
          │                                 │
          ▼                                 ▼
     Qt WebChannel                    Qt WebChannel
          │                                 │
          ▼                                 ▼
      Python Backend                  Python Backend
          │                                 │
          ▼                                 ▼
 Google Drive API                    PikePDF Engine
```

---

# ⚙ Workflow

## Google Drive Downloader

```
Excel / CSV

        │

        ▼

Read using Pandas

        │

        ▼

Extract Drive Links

        │

        ▼

Authenticate with Google

        │

        ▼

Multi-threaded Download

        │

        ▼

ZIP Generation

        │

        ▼

Downloads Folder
```

---

## PDF Merger

```
User Uploads PDFs

        │

        ▼

Encryption Detection

        │

        ▼

Worker Thread

        │

        ▼

Merge Engine

        │

        ▼

Save to Downloads
```

---

# 🛠 Technology Stack

| Category | Technologies |
|------------|----------------|
| Programming Language | Python 3 |
| Desktop Framework | PySide6 |
| Web UI | HTML, CSS, JavaScript |
| Embedded Browser | Qt WebEngine |
| Communication Layer | Qt WebChannel |
| Spreadsheet Processing | Pandas |
| Google Integration | Google Drive API |
| Authentication | OAuth 2.0 |
| PDF Processing | PikePDF |
| Packaging | PyInstaller |
| Installer | Inno Setup |

---

# 📂 Project Structure

```
NBA_Utilities/

├── src/
│
├── home.py
├── glink.py
├── merger.py
├── config.py
│
├── ui/
│   ├── nba-drive-downloader.html
│   ├── nba-pdf-merger.html
│   └── nba-utilities-home.html
│
├── assets/
│   └── icon.ico
│
├── build.py
├── installer.iss
├── build_nba_utilities.spec
├── requirements.txt
└── README.md
```

---

# 🚀 Installation

```bash
git clone https://github.com/mukeshkannanpk/NBA_Utilities.git

cd NBA_Utilities

python -m venv .venv

pip install -r requirements.txt
```

Add your Google OAuth `credentials.json` before running the Google Drive Downloader.

---

# 🔨 Build

```bash
python build.py
```

The automated build process:

- Verifies dependencies
- Builds executables using PyInstaller
- Creates installer-ready directory structure
- Generates deployment package

---

# 🧠 Technical Highlights

- Multi-threaded download engine using `QThread` and `ThreadPoolExecutor`
- OAuth 2.0 token refresh
- JavaScript ↔ Python communication using Qt WebChannel
- Cross-platform path management
- Production logging
- Automatic retry strategy
- Rate limiting for Google Drive API
- Temporary file management
- Standalone executable packaging

---

# 📄 License

Released under the MIT License.

---

## 👨‍💻 Author

**Mukesh kannan P K**

Designed, developed, tested, packaged and deployed as an end-to-end automation solution during internship at the **Training and Placement Cell, Bannari Amman Institute of Technology**.
