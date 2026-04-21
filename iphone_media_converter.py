"""
╔══════════════════════════════════════════════════════════╗
║          iPhone Media Batch Converter for Windows        ║
║          HEIC → JPG  |  MOV → MP4                       ║
╚══════════════════════════════════════════════════════════╝

Requirements (install once):
    pip install Pillow pillow-heif

FFmpeg is required for MOV → MP4 conversion:
    Download from https://ffmpeg.org/download.html
    Add ffmpeg.exe to your system PATH, or place it next to this script.

Usage:
    python iphone_media_converter.py
"""

import os
import sys
import threading
import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime

# ── GUI imports ──────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Check and import imaging libraries ───────────────────
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False


# ═════════════════════════════════════════════════════════
#  CONVERSION ENGINE
# ═════════════════════════════════════════════════════════

def find_ffmpeg():
    """Locate ffmpeg executable."""
    # Check next to this script
    script_dir = Path(__file__).parent
    local_ff = script_dir / "ffmpeg.exe"
    if local_ff.exists():
        return str(local_ff)
    # Check system PATH
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    return None


def convert_heic_to_jpg(src: Path, dst: Path, quality: int = 92) -> dict:
    """Convert a single HEIC/HEIF file to JPG."""
    result = {"src": str(src), "dst": str(dst), "ok": False, "msg": ""}
    try:
        img = Image.open(src)
        # Preserve EXIF orientation
        exif_data = img.info.get("exif", None)
        img = img.convert("RGB")
        save_kwargs = {"quality": quality, "optimize": True}
        if exif_data:
            save_kwargs["exif"] = exif_data
        img.save(dst, "JPEG", **save_kwargs)
        result["ok"] = True
        result["msg"] = f"{dst.stat().st_size / 1024:.0f} KB"
    except Exception as e:
        result["msg"] = str(e)
    return result


def convert_mov_to_mp4(src: Path, dst: Path, ffmpeg_path: str,
                       crf: int = 23, preset: str = "medium") -> dict:
    """Convert a single MOV file to MP4 using ffmpeg."""
    result = {"src": str(src), "dst": str(dst), "ok": False, "msg": ""}
    try:
        cmd = [
            ffmpeg_path,
            "-y",                   # overwrite
            "-i", str(src),
            "-c:v", "libx264",     # H.264 video codec
            "-crf", str(crf),       # quality (lower = better, 18-28 typical)
            "-preset", preset,
            "-c:a", "aac",         # AAC audio
            "-b:a", "192k",
            "-movflags", "+faststart",  # web-friendly
            "-pix_fmt", "yuv420p",      # maximum compatibility
            str(dst),
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if proc.returncode == 0:
            result["ok"] = True
            size_mb = dst.stat().st_size / (1024 * 1024)
            result["msg"] = f"{size_mb:.1f} MB"
        else:
            result["msg"] = proc.stderr[-300:] if proc.stderr else "ffmpeg error"
    except subprocess.TimeoutExpired:
        result["msg"] = "Timed out (>10 min)"
    except Exception as e:
        result["msg"] = str(e)
    return result


# ═════════════════════════════════════════════════════════
#  GUI APPLICATION
# ═════════════════════════════════════════════════════════

class ConverterApp:
    # Color palette
    BG          = "#1a1a2e"
    BG_CARD     = "#16213e"
    BG_INPUT    = "#0f3460"
    ACCENT      = "#e94560"
    ACCENT_DARK = "#c73e54"
    TEXT        = "#eaeaea"
    TEXT_DIM    = "#8892a4"
    SUCCESS     = "#2ecc71"
    WARNING     = "#f39c12"
    ERROR       = "#e74c3c"
    BORDER      = "#233554"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("iPhone Media Converter")
        self.root.geometry("780x720")
        self.root.minsize(700, 600)
        self.root.configure(bg=self.BG)

        # Try to set icon / dark title bar on Windows
        if sys.platform == "win32":
            try:
                from ctypes import windll
                windll.dwmapi.DwmSetWindowAttribute(
                    windll.user32.GetParent(root.winfo_id()),
                    20, byref(c_int(2)), sizeof(c_int(2)))
            except Exception:
                pass

        self.files = []          # list of Path objects
        self.converting = False
        self.ffmpeg_path = find_ffmpeg()

        self._build_styles()
        self._build_ui()
        self._check_dependencies()

    # ── Styles ───────────────────────────────────────────
    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Main.TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.BG_CARD)
        style.configure("Title.TLabel", background=self.BG,
                        foreground=self.ACCENT, font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", background=self.BG,
                        foreground=self.TEXT_DIM, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=self.BG_CARD,
                        foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("CardBold.TLabel", background=self.BG_CARD,
                        foreground=self.TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("Status.TLabel", background=self.BG,
                        foreground=self.TEXT_DIM, font=("Segoe UI", 9))
        style.configure("Dep.TLabel", background=self.BG_CARD,
                        foreground=self.SUCCESS, font=("Segoe UI", 9))
        style.configure("DepWarn.TLabel", background=self.BG_CARD,
                        foreground=self.WARNING, font=("Segoe UI", 9))
        style.configure("DepErr.TLabel", background=self.BG_CARD,
                        foreground=self.ERROR, font=("Segoe UI", 9))

        # Custom progress bar
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=self.BG_INPUT,
                        background=self.ACCENT,
                        thickness=8)

    # ── UI Layout ────────────────────────────────────────
    def _build_ui(self):
        main = ttk.Frame(self.root, style="Main.TFrame")
        main.pack(fill="both", expand=True, padx=24, pady=16)

        # Header
        ttk.Label(main, text="⚡ iPhone Media Converter", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="Batch convert HEIC → JPG  and  MOV → MP4  for Windows",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        # Dependency status card
        dep_card = ttk.Frame(main, style="Card.TFrame")
        dep_card.pack(fill="x", pady=(0, 10), ipady=8, ipadx=12)

        ttk.Label(dep_card, text="Dependencies", style="CardBold.TLabel").pack(anchor="w", padx=12, pady=(8, 4))
        self.lbl_pil = ttk.Label(dep_card, text="", style="Dep.TLabel")
        self.lbl_pil.pack(anchor="w", padx=20)
        self.lbl_heif = ttk.Label(dep_card, text="", style="Dep.TLabel")
        self.lbl_heif.pack(anchor="w", padx=20)
        self.lbl_ffmpeg = ttk.Label(dep_card, text="", style="Dep.TLabel")
        self.lbl_ffmpeg.pack(anchor="w", padx=20, pady=(0, 6))

        # ── Input / Output ───────────────────────────────
        io_frame = ttk.Frame(main, style="Main.TFrame")
        io_frame.pack(fill="x", pady=(4, 6))

        # Add files button
        btn_frame = ttk.Frame(io_frame, style="Main.TFrame")
        btn_frame.pack(fill="x")

        self.btn_add = tk.Button(
            btn_frame, text="＋  Add Files or Folder",
            font=("Segoe UI", 11, "bold"), fg="white", bg=self.ACCENT,
            activebackground=self.ACCENT_DARK, activeforeground="white",
            relief="flat", cursor="hand2", padx=16, pady=8,
            command=self._add_files)
        self.btn_add.pack(side="left")

        self.btn_add_folder = tk.Button(
            btn_frame, text="📁  Add Folder",
            font=("Segoe UI", 10), fg=self.TEXT, bg=self.BG_INPUT,
            activebackground=self.BORDER, activeforeground="white",
            relief="flat", cursor="hand2", padx=12, pady=8,
            command=self._add_folder)
        self.btn_add_folder.pack(side="left", padx=(8, 0))

        self.btn_clear = tk.Button(
            btn_frame, text="✕ Clear",
            font=("Segoe UI", 10), fg=self.TEXT_DIM, bg=self.BG_CARD,
            activebackground=self.BORDER, activeforeground="white",
            relief="flat", cursor="hand2", padx=12, pady=8,
            command=self._clear_files)
        self.btn_clear.pack(side="right")

        # Output directory
        out_frame = ttk.Frame(main, style="Main.TFrame")
        out_frame.pack(fill="x", pady=(4, 6))
        ttk.Label(out_frame, text="Output folder:", style="Sub.TLabel").pack(side="left")
        self.out_var = tk.StringVar(value="(same as source)")
        self.out_entry = tk.Entry(out_frame, textvariable=self.out_var,
                                  bg=self.BG_INPUT, fg=self.TEXT,
                                  insertbackground=self.TEXT, relief="flat",
                                  font=("Segoe UI", 9))
        self.out_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=4)
        tk.Button(out_frame, text="Browse", font=("Segoe UI", 9),
                  fg=self.TEXT, bg=self.BG_INPUT, relief="flat",
                  command=self._pick_output, cursor="hand2").pack(side="right")

        # ── File list ────────────────────────────────────
        list_frame = ttk.Frame(main, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True, pady=(4, 8))

        cols = ("file", "type", "size", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=10)
        self.tree.heading("file", text="File")
        self.tree.heading("type", text="Convert")
        self.tree.heading("size", text="Size")
        self.tree.heading("status", text="Status")
        self.tree.column("file", width=320, minwidth=200)
        self.tree.column("type", width=100, anchor="center")
        self.tree.column("size", width=80, anchor="center")
        self.tree.column("status", width=160, anchor="center")

        # Treeview colors
        style = ttk.Style()
        style.configure("Treeview",
                        background=self.BG_CARD, foreground=self.TEXT,
                        fieldbackground=self.BG_CARD, font=("Segoe UI", 9),
                        rowheight=26)
        style.configure("Treeview.Heading",
                        background=self.BG_INPUT, foreground=self.TEXT,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", self.BG_INPUT)])

        self.tree.tag_configure("done", foreground=self.SUCCESS)
        self.tree.tag_configure("error", foreground=self.ERROR)
        self.tree.tag_configure("working", foreground=self.WARNING)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Settings row ─────────────────────────────────
        settings = ttk.Frame(main, style="Main.TFrame")
        settings.pack(fill="x", pady=(0, 4))

        ttk.Label(settings, text="JPG Quality:", style="Sub.TLabel").pack(side="left")
        self.quality_var = tk.IntVar(value=92)
        self.quality_spin = tk.Spinbox(settings, from_=50, to=100,
                                        textvariable=self.quality_var, width=4,
                                        bg=self.BG_INPUT, fg=self.TEXT,
                                        buttonbackground=self.BG_INPUT,
                                        relief="flat", font=("Segoe UI", 10))
        self.quality_spin.pack(side="left", padx=(4, 16))

        ttk.Label(settings, text="Video CRF:", style="Sub.TLabel").pack(side="left")
        self.crf_var = tk.IntVar(value=23)
        self.crf_spin = tk.Spinbox(settings, from_=15, to=35,
                                    textvariable=self.crf_var, width=4,
                                    bg=self.BG_INPUT, fg=self.TEXT,
                                    buttonbackground=self.BG_INPUT,
                                    relief="flat", font=("Segoe UI", 10))
        self.crf_spin.pack(side="left", padx=(4, 8))
        ttk.Label(settings, text="(lower = better quality, bigger file)",
                  style="Sub.TLabel").pack(side="left")

        # ── Progress + Convert ───────────────────────────
        bottom = ttk.Frame(main, style="Main.TFrame")
        bottom.pack(fill="x", pady=(4, 0))

        self.progress = ttk.Progressbar(bottom, mode="determinate",
                                         style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 8))

        btn_row = ttk.Frame(bottom, style="Main.TFrame")
        btn_row.pack(fill="x")

        self.lbl_status = ttk.Label(btn_row, text="Ready — add files to begin",
                                     style="Status.TLabel")
        self.lbl_status.pack(side="left")

        self.btn_convert = tk.Button(
            btn_row, text="▶  Convert All",
            font=("Segoe UI", 12, "bold"), fg="white", bg=self.ACCENT,
            activebackground=self.ACCENT_DARK, activeforeground="white",
            relief="flat", cursor="hand2", padx=24, pady=6,
            command=self._start_conversion)
        self.btn_convert.pack(side="right")

    # ── Dependency check ─────────────────────────────────
    def _check_dependencies(self):
        if HAS_PIL:
            self.lbl_pil.configure(text="✓  Pillow (image processing)", style="Dep.TLabel")
        else:
            self.lbl_pil.configure(text="✗  Pillow — run: pip install Pillow", style="DepErr.TLabel")

        if HAS_HEIF:
            self.lbl_heif.configure(text="✓  pillow-heif (HEIC support)", style="Dep.TLabel")
        else:
            self.lbl_heif.configure(text="✗  pillow-heif — run: pip install pillow-heif", style="DepErr.TLabel")

        if self.ffmpeg_path:
            self.lbl_ffmpeg.configure(text=f"✓  FFmpeg found: {self.ffmpeg_path}", style="Dep.TLabel")
        else:
            self.lbl_ffmpeg.configure(text="✗  FFmpeg not found — required for MOV→MP4", style="DepWarn.TLabel")

    # ── File management ──────────────────────────────────
    SUPPORTED_EXT = {".heic", ".heif", ".mov"}

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select iPhone media files",
            filetypes=[
                ("iPhone Media", "*.heic *.heif *.HEIC *.HEIF *.mov *.MOV"),
                ("HEIC Images", "*.heic *.heif *.HEIC *.HEIF"),
                ("MOV Videos", "*.mov *.MOV"),
                ("All Files", "*.*"),
            ])
        for p in paths:
            self._insert_file(Path(p))
        self._update_status()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select folder with iPhone media")
        if not folder:
            return
        folder_path = Path(folder)
        count = 0
        for f in sorted(folder_path.iterdir()):
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXT:
                self._insert_file(f)
                count += 1
        if count == 0:
            messagebox.showinfo("No files found",
                                "No HEIC or MOV files found in that folder.")
        self._update_status()

    def _insert_file(self, path: Path):
        if path in self.files:
            return
        self.files.append(path)
        ext = path.suffix.lower()
        conv_type = "HEIC → JPG" if ext in (".heic", ".heif") else "MOV → MP4"
        size_mb = path.stat().st_size / (1024 * 1024)
        size_str = f"{size_mb:.1f} MB" if size_mb >= 1 else f"{path.stat().st_size / 1024:.0f} KB"
        self.tree.insert("", "end", iid=str(path),
                         values=(path.name, conv_type, size_str, "Pending"))

    def _clear_files(self):
        self.files.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress["value"] = 0
        self._update_status()

    def _pick_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.out_var.set(folder)

    def _update_status(self):
        heic_count = sum(1 for f in self.files if f.suffix.lower() in (".heic", ".heif"))
        mov_count = sum(1 for f in self.files if f.suffix.lower() == ".mov")
        if not self.files:
            self.lbl_status.configure(text="Ready — add files to begin")
        else:
            self.lbl_status.configure(
                text=f"{len(self.files)} file(s): {heic_count} images, {mov_count} videos")

    # ── Conversion ───────────────────────────────────────
    def _get_output_path(self, src: Path, new_ext: str) -> Path:
        out_dir_str = self.out_var.get().strip()
        if out_dir_str in ("", "(same as source)"):
            out_dir = src.parent
        else:
            out_dir = Path(out_dir_str)
            out_dir.mkdir(parents=True, exist_ok=True)

        dst = out_dir / (src.stem + new_ext)
        # Avoid overwriting
        counter = 1
        while dst.exists():
            dst = out_dir / f"{src.stem}_{counter}{new_ext}"
            counter += 1
        return dst

    def _start_conversion(self):
        if self.converting:
            return
        if not self.files:
            messagebox.showwarning("No files", "Add some HEIC or MOV files first.")
            return

        # Validate dependencies for queued file types
        has_heic = any(f.suffix.lower() in (".heic", ".heif") for f in self.files)
        has_mov = any(f.suffix.lower() == ".mov" for f in self.files)

        if has_heic and (not HAS_PIL or not HAS_HEIF):
            messagebox.showerror("Missing dependency",
                                 "Install Pillow and pillow-heif to convert HEIC files:\n\n"
                                 "pip install Pillow pillow-heif")
            return
        if has_mov and not self.ffmpeg_path:
            messagebox.showerror("FFmpeg not found",
                                 "FFmpeg is required for MOV → MP4 conversion.\n\n"
                                 "Download from https://ffmpeg.org/download.html\n"
                                 "and add to your PATH or place next to this script.")
            return

        self.converting = True
        self.btn_convert.configure(state="disabled", text="⏳  Converting…")
        self.btn_add.configure(state="disabled")
        self.btn_add_folder.configure(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.files)

        thread = threading.Thread(target=self._convert_all, daemon=True)
        thread.start()

    def _convert_all(self):
        quality = self.quality_var.get()
        crf = self.crf_var.get()
        total = len(self.files)
        ok_count = 0
        err_count = 0

        for i, src in enumerate(self.files):
            ext = src.suffix.lower()

            # Update status to "working"
            self.root.after(0, lambda s=src: self.tree.item(
                str(s), values=(s.name,
                                self.tree.item(str(s))["values"][1],
                                self.tree.item(str(s))["values"][2],
                                "Converting…"), tags=("working",)))

            if ext in (".heic", ".heif"):
                dst = self._get_output_path(src, ".jpg")
                result = convert_heic_to_jpg(src, dst, quality)
            elif ext == ".mov":
                dst = self._get_output_path(src, ".mp4")
                result = convert_mov_to_mp4(src, dst, self.ffmpeg_path, crf)
            else:
                result = {"ok": False, "msg": "Unsupported format"}

            if result["ok"]:
                ok_count += 1
                tag = "done"
                status = f"✓  {result['msg']}"
            else:
                err_count += 1
                tag = "error"
                status = f"✗  {result['msg'][:50]}"

            # Update tree row
            self.root.after(0, lambda s=src, st=status, t=tag: self.tree.item(
                str(s), values=(s.name,
                                self.tree.item(str(s))["values"][1],
                                self.tree.item(str(s))["values"][2],
                                st), tags=(t,)))

            # Update progress
            self.root.after(0, lambda v=i + 1: self._set_progress(v))

            # Update status label
            self.root.after(0, lambda o=ok_count, e=err_count, t=total:
                            self.lbl_status.configure(
                                text=f"Progress: {o + e}/{t}  —  ✓ {o}  ✗ {e}"))

        # Done
        self.root.after(0, lambda: self._conversion_done(ok_count, err_count))

    def _set_progress(self, value):
        self.progress["value"] = value

    def _conversion_done(self, ok_count, err_count):
        self.converting = False
        self.btn_convert.configure(state="normal", text="▶  Convert All")
        self.btn_add.configure(state="normal")
        self.btn_add_folder.configure(state="normal")
        self.lbl_status.configure(
            text=f"Done!  ✓ {ok_count} converted  ✗ {err_count} failed")

        if err_count == 0:
            messagebox.showinfo("Conversion Complete",
                                f"All {ok_count} file(s) converted successfully!")
        else:
            messagebox.showwarning("Conversion Complete",
                                   f"Converted: {ok_count}\nFailed: {err_count}\n\n"
                                   "Check the status column for error details.")


# ═════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app = ConverterApp(root)
    root.mainloop()
