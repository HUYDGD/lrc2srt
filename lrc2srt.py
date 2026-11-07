import os
import re
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


class App:
    def __init__(self, root):
        self.root = root
        root.title("LRC → SRT")
        root.geometry("260x130")
        root.resizable(False, False)

        self.button = tk.Button(
            root,
            text="Choose LRC file(s)",
            font=("Segoe UI", 11),
            command=self.convert,
        )
        self.button.pack(expand=True, ipadx=12, ipady=8, pady=(20, 6))

        self.status = tk.Label(root, text="", fg="gray")
        self.status.pack(pady=(0, 10))

    def convert(self):
        files = askopenfilenames(
            parent=self.root,
            title="Select LRC file(s)",
            filetypes=[("LRC files", "*.lrc"), ("All files", "*.*")],
        )
        if not files:
            return

        done, failed = 0, []
        for lrc_path in files:
            srt_path = os.path.splitext(lrc_path)[0] + '.srt'
            try:
                lrc_to_srt(lrc_path, srt_path)
                done += 1
            except Exception as e:
                failed.append(f"{os.path.basename(lrc_path)}: {e}")

        self.status.config(text=f"Converted {done} of {len(files)} file(s)")
        if failed:
            messagebox.showerror("Some files failed", "\n".join(failed))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()