"""
Ultimate Showdown — Game Launcher & Auto-Updater
================================================
Requires:  pip install customtkinter requests pillow
Build exe: pyinstaller --onefile --windowed --icon=icon.ico --name="UltimateShowdown Launcher" launcher.py
"""

import os
import sys
import json
import shutil
import zipfile
import threading
import subprocess
import traceback
from pathlib import Path

import requests
import customtkinter as ctk
from tkinter import messagebox

# ── CONFIG ─────────────────────────────────────────────────────────────────────
GITHUB_REPO      = "SoomMedia/ultimate-showdown-demo"        # ← change this
GAME_EXE         = Path("game") / "Ultimate Showdown.exe"  # ← change this
VERSION_FILE     = Path("version.txt")
INSTALL_DIR      = Path("game")
TEMP_ZIP         = Path("_update.zip")

WINDOW_TITLE     = "Ultimate Showdown"
WINDOW_SIZE      = "520x340"
ACCENT_COLOR     = "#E83030"
ACCENT_HOVER     = "#FF5252"
BG_COLOR         = "#0D0D0F"
PANEL_COLOR      = "#141418"
BORDER_COLOR     = "#2A2A32"
TEXT_PRIMARY     = "#F0F0F0"
TEXT_SECONDARY   = "#888899"
# ───────────────────────────────────────────────────────────────────────────────


def resource_path(relative: str) -> str:
    """Resolve paths correctly when running as a PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base) / relative)


class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.resizable(False, False)
        self.configure(fg_color=BG_COLOR)

        self._build_ui()
        self.after(200, self._start_check)

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──
        header = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_lbl = ctk.CTkLabel(
            header,
            text="ULTIMATE SHOWDOWN",
            font=ctk.CTkFont(family="Georgia", size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        title_lbl.place(relx=0.5, rely=0.42, anchor="center")

        self.version_lbl = ctk.CTkLabel(
            header,
            text="Checking for updates…",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY,
        )
        self.version_lbl.place(relx=0.5, rely=0.76, anchor="center")

        # ── Body ──
        body = ctk.CTkFrame(self, fg_color=BG_COLOR)
        body.pack(fill="both", expand=True, padx=28, pady=(22, 0))

        # Status icon + label row
        status_row = ctk.CTkFrame(body, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 10))

        self.status_dot = ctk.CTkLabel(
            status_row, text="●", font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY, width=18
        )
        self.status_dot.pack(side="left")

        self.status_lbl = ctk.CTkLabel(
            status_row,
            text="Initializing…",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.status_lbl.pack(side="left", padx=(6, 0))

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            body, height=8, corner_radius=4,
            fg_color=BORDER_COLOR,
            progress_color=ACCENT_COLOR,
        )
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(4, 6))

        # Detail label (speed / file info)
        self.detail_lbl = ctk.CTkLabel(
            body, text="", font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY, anchor="w"
        )
        self.detail_lbl.pack(fill="x")

        # ── Footer ──
        footer = ctk.CTkFrame(self, fg_color=PANEL_COLOR, corner_radius=0, height=64)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self.action_btn = ctk.CTkButton(
            footer,
            text="Please wait…",
            width=200, height=38,
            corner_radius=6,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFFFFF",
            state="disabled",
            command=self._on_action,
        )
        self.action_btn.place(relx=0.5, rely=0.5, anchor="center")

    # ── State helpers ──────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = TEXT_SECONDARY, dot: str = "●"):
        self.status_lbl.configure(text=text, text_color=color)
        self.status_dot.configure(text=dot, text_color=color)

    def _set_detail(self, text: str):
        self.detail_lbl.configure(text=text)

    def _set_progress(self, value: float):
        self.progress.set(value)

    def _ready_to_launch(self, local_ver: str, latest_ver: str):
        self.version_lbl.configure(text=f"Version {local_ver}  •  Latest {latest_ver}")
        self._set_status("Up to date — ready to play!", color="#50E878", dot="●")
        self._set_progress(1.0)
        self.action_btn.configure(text="▶  PLAY", state="normal")

    def _update_available(self, local_ver: str | None, latest_ver: str):
        local_str = local_ver if local_ver else "not installed"
        self.version_lbl.configure(text=f"Installed: {local_str}  →  Latest: {latest_ver}")
        self._set_status("Update available!", color="#FFC040", dot="▲")
        self.action_btn.configure(text="⬇  UPDATE & PLAY", state="normal")

    def _set_error(self, title: str, msg: str):
        self._set_status(f"Error: {title}", color="#FF4444", dot="✕")
        self._set_detail(msg[:120])
        self.action_btn.configure(text="↺  RETRY", state="normal")
        self._mode = "retry"

    # ── Logic ──────────────────────────────────────────────────────────────────

    _mode = "wait"  # wait | launch | update | retry

    def _on_action(self):
        if self._mode == "launch":
            self._launch_game()
        elif self._mode == "update":
            self.action_btn.configure(state="disabled")
            threading.Thread(target=self._do_update, daemon=True).start()
        elif self._mode == "retry":
            self._mode = "wait"
            self.action_btn.configure(text="Please wait…", state="disabled")
            self._set_detail("")
            self._set_progress(0)
            self.after(100, self._start_check)

    def _start_check(self):
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _check_for_updates(self):
        self.after(0, lambda: self._set_status("Checking for updates…"))
        try:
            latest_ver, download_url = self._fetch_latest_release()
        except requests.exceptions.ConnectionError:
            # Offline — launch local version if present
            local_ver = self._read_local_version()
            if local_ver and GAME_EXE.exists():
                self.after(0, lambda: self._set_status(
                    "Offline — using cached version", color="#FFC040", dot="◎"))
                self.after(0, lambda: self.version_lbl.configure(
                    text=f"Version {local_ver}  (offline)"))
                self._mode = "launch"
                self.after(0, lambda: self.action_btn.configure(
                    text="▶  PLAY (offline)", state="normal"))
            else:
                self.after(0, lambda: self._set_error(
                    "No internet connection",
                    "Connect to the internet to download the game for the first time."))
            return
        except Exception as exc:
            self.after(0, lambda: self._set_error("Update check failed", str(exc)))
            return

        local_ver = self._read_local_version()

        if local_ver == latest_ver and GAME_EXE.exists():
            self._mode = "launch"
            self.after(0, lambda: self._ready_to_launch(local_ver, latest_ver))
        else:
            self._pending_download = (latest_ver, download_url)
            self._mode = "update"
            self.after(0, lambda: self._update_available(local_ver, latest_ver))

    def _do_update(self):
        latest_ver, download_url = self._pending_download
        try:
            self._download(download_url)
            self._extract()
            self._write_local_version(latest_ver)
            self.after(0, lambda: self._ready_to_launch(latest_ver, latest_ver))
            self._mode = "launch"
        except Exception as exc:
            traceback.print_exc()
            self.after(0, lambda: self._set_error("Update failed", str(exc)))

    def _launch_game(self):
        if not GAME_EXE.exists():
            messagebox.showerror("Launch Error", f"Game executable not found:\n{GAME_EXE}")
            return
        try:
            subprocess.Popen([str(GAME_EXE)], cwd=str(INSTALL_DIR))
            self.after(800, self.destroy)
        except Exception as exc:
            messagebox.showerror("Launch Error", f"Could not start the game:\n{exc}")

    # ── GitHub helpers ─────────────────────────────────────────────────────────

    def _fetch_latest_release(self) -> tuple[str, str]:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        tag = data.get("tag_name", "")
        if not tag:
            raise ValueError("No tag_name in GitHub release response.")

        assets = data.get("assets", [])
        # Prefer .zip asset; fall back to first asset
        zip_asset = next(
            (a for a in assets if a["name"].endswith(".zip")), None
        ) or (assets[0] if assets else None)

        if not zip_asset:
            raise ValueError("No downloadable assets found in latest release.")

        return tag, zip_asset["browser_download_url"]

    # ── File helpers ───────────────────────────────────────────────────────────

    def _read_local_version(self) -> str | None:
        return VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else None

    def _write_local_version(self, ver: str):
        VERSION_FILE.write_text(ver)

    def _download(self, url: str):
        self.after(0, lambda: self._set_status("Downloading update…", color=TEXT_PRIMARY))
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 65536  # 64 KB

        with open(TEMP_ZIP, "wb") as f:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total
                        dl_mb = downloaded / 1_048_576
                        total_mb = total / 1_048_576
                        detail = f"{dl_mb:.1f} MB / {total_mb:.1f} MB"
                        self.after(0, lambda p=pct, d=detail: (
                            self._set_progress(p),
                            self._set_detail(d),
                        ))

    def _extract(self):
        self.after(0, lambda: self._set_status("Extracting files…", color=TEXT_PRIMARY))
        self.after(0, lambda: self._set_detail(""))
        self.after(0, lambda: self._set_progress(0))

        if INSTALL_DIR.exists():
            shutil.rmtree(INSTALL_DIR)
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(TEMP_ZIP, "r") as zf:
            names = zf.namelist()
            total = len(names)
            for i, name in enumerate(names):
                zf.extract(name, INSTALL_DIR)
                self.after(0, lambda p=(i + 1) / total: self._set_progress(p))

        TEMP_ZIP.unlink(missing_ok=True)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
