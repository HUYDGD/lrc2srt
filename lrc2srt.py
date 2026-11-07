import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
from tkinter.filedialog import askopenfilenames


def parse_lrc_timestamp(timestamp):
    try:
        minutes, rest = timestamp.split(':')
        seconds, fraction = rest.split('.')
        return int(minutes) * 60 + int(seconds) + float(f"0.{fraction}")
    except ValueError:
        return None


def format_time(seconds):
    total_ms = round(seconds * 1000)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def lrc_to_srt(lrc_file_path, srt_file_path):
    with open(lrc_file_path, 'r', encoding='utf-8') as f:
        lrc_content = f.read()

    matches = re.findall(r'\[(\d+:\d+\.\d+)\](.*)', lrc_content)

    blocks = []
    for idx, (timestamp, text) in enumerate(matches):
        start = parse_lrc_timestamp(timestamp)
        text = text.strip()
        if start is None or not text:
            continue

        end = parse_lrc_timestamp(matches[idx + 1][0]) if idx + 1 < len(matches) else None
        if end is None:
            end = start + 1

        blocks.append(
            f"{len(blocks) + 1}\n{format_time(start)} --> {format_time(end)}\n{text}\n"
        )

    with open(srt_file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(blocks))


def open_with_default_app(path):
    if sys.platform.startswith('win'):
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', path])
    else:
        subprocess.run(['xdg-open', path])


def show_in_folder(path):
    """Open the folder containing the file, with the file highlighted where supported."""
    path = os.path.normpath(path)
    if sys.platform.startswith('win'):
        subprocess.Popen(['explorer', '/select,', path])  # explorer returns exit code 1 normally
    elif sys.platform == 'darwin':
        subprocess.run(['open', '-R', path])  # reveal in Finder
    else:
        subprocess.run(['xdg-open', os.path.dirname(path)])


class App:
    def __init__(self, root):
        self.root = root
        root.title("LRC → SRT")
        root.geometry("300x210")
        root.resizable(False, False)

        self.open_after = tk.BooleanVar(value=False)
        self.show_folder = tk.BooleanVar(value=True)

        self.button = tk.Button(
            root,
            text="Choose LRC file(s)",
            font=("Segoe UI", 11),
            command=self.convert,
        )
        self.button.pack(ipadx=12, ipady=8, pady=(20, 10))

        tk.Checkbutton(
            root, text="Open .srt after converting", variable=self.open_after
        ).pack(anchor="w", padx=40)
        tk.Checkbutton(
            root, text="Show .srt location in folder", variable=self.show_folder
        ).pack(anchor="w", padx=40)

        self.status = tk.Label(root, text="", fg="gray")
        self.status.pack(pady=(10, 10))

    def convert(self):
        files = askopenfilenames(
            parent=self.root,
            title="Select LRC file(s)",
            filetypes=[("LRC files", "*.lrc"), ("All files", "*.*")],
        )
        if not files:
            return

        converted, failed = [], []
        for lrc_path in files:
            srt_path = os.path.splitext(lrc_path)[0] + '.srt'
            try:
                lrc_to_srt(lrc_path, srt_path)
                converted.append(srt_path)
            except Exception as e:
                failed.append(f"{os.path.basename(lrc_path)}: {e}")

        self.status.config(text=f"Converted {len(converted)} of {len(files)} file(s)")

        if failed:
            messagebox.showerror("Some files failed", "\n".join(failed))

        if converted and self.show_folder.get():
            # One window per folder, not one per file
            seen_folders = set()
            for path in converted:
                folder = os.path.dirname(path)
                if folder in seen_folders:
                    continue
                seen_folders.add(folder)
                try:
                    show_in_folder(path)
                except Exception as e:
                    messagebox.showerror("Can't open folder", f"{folder}\n\n{e}")

        if converted and self.open_after.get():
            for path in converted:
                try:
                    open_with_default_app(path)
                except Exception as e:
                    messagebox.showerror("Can't open file", f"{path}\n\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()