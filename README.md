# iPhone Media Batch Converter for Windows

Convert iPhone photos and videos to universally compatible formats:
- **HEIC / HEIF → JPG** (with EXIF preservation)
- **MOV → MP4** (H.264 + AAC, web-friendly)

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Windows](https://img.shields.io/badge/OS-Windows-green)

---

## Quick Start

**Option A — Double-click the launcher:**
1. Double-click `LAUNCH.bat` — it installs dependencies and starts the app.

**Option B — Manual setup:**
```
pip install Pillow pillow-heif
python iphone_media_converter.py
```

## Requirements

| Component | Purpose | Install |
|-----------|---------|---------|
| **Python 3.8+** | Runtime | [python.org](https://www.python.org/downloads/) — check "Add to PATH" |
| **Pillow** | Image processing | `pip install Pillow` |
| **pillow-heif** | HEIC/HEIF decoding | `pip install pillow-heif` |
| **FFmpeg** | MOV→MP4 video conversion | [ffmpeg.org](https://ffmpeg.org/download.html) |

### Installing FFmpeg on Windows

1. Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) (choose a Windows build)
2. Extract the archive
3. Either:
   - Copy `ffmpeg.exe` next to `iphone_media_converter.py`, **or**
   - Add the FFmpeg `bin` folder to your system PATH

## Features

- **Batch processing** — drag in hundreds of files at once
- **Folder scanning** — point at your DCIM folder and it finds all HEIC/MOV files
- **Quality controls** — adjustable JPG quality (50–100) and video CRF (15–35)
- **EXIF preservation** — photo orientation and metadata carried over to JPG
- **Smart output** — saves next to originals or to a custom output folder
- **No overwrites** — auto-renames if output file already exists
- **Progress tracking** — real-time status for each file with success/error reporting
- **Dependency check** — shows what's installed and what's missing on launch

## Settings

| Setting | Default | Range | Notes |
|---------|---------|-------|-------|
| JPG Quality | 92 | 50–100 | Higher = better quality, larger file |
| Video CRF | 23 | 15–35 | Lower = better quality, larger file. 18 is visually lossless |

## Typical Workflow

1. Connect iPhone to PC (or copy photos to a folder)
2. Launch the converter
3. Click **Add Folder** → navigate to your iPhone's DCIM folder
4. Optionally set an output folder
5. Click **Convert All**
6. Done — your JPGs and MP4s are ready to use anywhere
