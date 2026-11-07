import ctypes
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilenames

# ---------- Conversion logic ----------

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


# ---------- OS helpers ----------

def open_with_default_app(path):
    if sys.platform.startswith('win'):
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', path])
    else:
        subprocess.run(['xdg-open', path])


def show_in_folder(path):
    path = os.path.normpath(path)
    if sys.platform.startswith('win'):
        subprocess.Popen(['explorer', '/select,', path])
    elif sys.platform == 'darwin':
        subprocess.run(['open', '-R', path])
    else:
        subprocess.run(['xdg-open', os.path.dirname(path)])


# ---------- UI ----------

BG = "#f3f4f8"
CARD = "#ffffff"
ACCENT = "#0077b6"
ACCENT_HOVER = "#01497c"
ACCENT_PRESSED = "#1d2d44"
TEXT = "#1f2937"
MUTED = "#6b7280"
OK = "#16a34a"
ERR = "#dc2626"
BORDER = "#e5e7eb"

FONT = "Segoe UI" if sys.platform.startswith('win') else " "


class App:
    def __init__(self, root):
        self.root = root
        self.srt_paths = {}  # tree item id -> srt path

        root.title("LRC2SRT Converter")
        root.geometry("460x520")
        root.minsize(480, 460)
        root.configure(bg=BG)

        self.open_after = tk.BooleanVar(value=False)
        self.show_folder = tk.BooleanVar(value=True)

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)

        s.configure("Title.TLabel", background=BG, foreground=TEXT,
                    font=(FONT, 18, "bold"))
        s.configure("Sub.TLabel", background=BG, foreground=MUTED,
                    font=(FONT, 10))
        s.configure("CardTitle.TLabel", background=CARD, foreground=MUTED,
                    font=(FONT, 9, "bold"))
        s.configure("Status.TLabel", background=BG, foreground=MUTED,
                    font=(FONT, 10))

        s.configure("Accent.TButton", background=ACCENT, foreground="white",
                    font=(FONT, 11, "bold"), padding=(16, 12),
                    borderwidth=0, focusthickness=0, relief="flat")
        s.map("Accent.TButton",
              background=[("pressed", ACCENT_PRESSED), ("active", ACCENT_HOVER)])

        s.configure("Card.TCheckbutton", background=CARD, foreground=TEXT,
                    font=(FONT, 10), focusthickness=0)
        s.map("Card.TCheckbutton", background=[("active", CARD)])

        s.configure("Treeview", background=CARD, fieldbackground=CARD,
                    foreground=TEXT, rowheight=30, borderwidth=0,
                    font=(FONT, 10))
        s.configure("Treeview.Heading", background=CARD, foreground=MUTED,
                    font=(FONT, 9, "bold"), borderwidth=0, relief="flat",
                    padding=(8, 6))
        s.map("Treeview.Heading", background=[("active", CARD)])
        s.map("Treeview", background=[("selected", "#eef2ff")],
              foreground=[("selected", TEXT)])
        s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        s.configure("Vertical.TScrollbar", background=BORDER, troughcolor=CARD,
                    borderwidth=0, arrowsize=12)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=24)
        outer.pack(fill="both", expand=True)

        # Header
        ttk.Label(outer, text="LRC2SRT", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Convert lyric files into subtitle files.",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 16))

        # Main button
        ttk.Button(outer, text="Choose LRC file(s)", style="Accent.TButton",
                   command=self.convert, cursor="hand2").pack(fill="x")

        # Results card
        results = tk.Frame(outer, bg=CARD, highlightbackground=BORDER,
                           highlightthickness=1)
        results.pack(fill="both", expand=True, pady=(16, 12))

        self.tree = ttk.Treeview(results, columns=("file", "status"),
                                 show="headings", selectmode="browse")
        self.tree.heading("file", text="FILE", anchor="w")
        self.tree.heading("status", text="STATUS", anchor="w")
        self.tree.column("file", width=300, anchor="w")
        self.tree.column("status", width=160, anchor="w")
        self.tree.tag_configure("ok", foreground=OK)
        self.tree.tag_configure("err", foreground=ERR)

        scroll = ttk.Scrollbar(results, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_row_double_click)

        # Empty-state hint
        self.hint = tk.Label(results, bg=CARD, fg=MUTED, font=(FONT, 10),
                             text="Converted files will appear here.\n"
                                  "Double-click a row to show it in its folder.")
        self.hint.place(relx=0.5, rely=0.5, anchor="center")

        # Options card
        options = ttk.Frame(outer, style="Card.TFrame", padding=(16, 12))
        options.pack(fill="x")
        ttk.Label(options, text="AFTER CONVERTING", style="CardTitle.TLabel").pack(
            anchor="w", pady=(0, 6))
        ttk.Checkbutton(options, text="Show .srt location in folder",
                        variable=self.show_folder,
                        style="Card.TCheckbutton").pack(anchor="w", pady=2)
        ttk.Checkbutton(options, text="Open .srt in default app",
                        variable=self.open_after,
                        style="Card.TCheckbutton").pack(anchor="w", pady=2)

        # Status
        self.status = ttk.Label(outer, text="Ready", style="Status.TLabel")
        self.status.pack(anchor="w", pady=(12, 0))

    def on_row_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        path = self.srt_paths.get(iid)
        if path and os.path.exists(path):
            try:
                show_in_folder(path)
            except Exception as e:
                self.status.config(text=f"Can't open folder: {e}")

    def convert(self):
        files = askopenfilenames(
            parent=self.root,
            title="Select LRC file(s)",
            filetypes=[("LRC files", "*.lrc"), ("All files", "*.*")],
        )
        if not files:
            return

        # Reset results
        self.tree.delete(*self.tree.get_children())
        self.srt_paths.clear()
        self.hint.place_forget()

        converted = []
        for lrc_path in files:
            srt_path = os.path.splitext(lrc_path)[0] + '.srt'
            name = os.path.basename(lrc_path)
            try:
                lrc_to_srt(lrc_path, srt_path)
                iid = self.tree.insert("", "end", values=(name, "✓ Converted"),
                                       tags=("ok",))
                self.srt_paths[iid] = srt_path
                converted.append(srt_path)
            except Exception as e:
                msg = str(e)
                if len(msg) > 40:
                    msg = msg[:37] + "..."
                self.tree.insert("", "end", values=(name, f"✗ {msg}"),
                                 tags=("err",))

        failed = len(files) - len(converted)
        text = f"Converted {len(converted)} of {len(files)} file(s)"
        if failed:
            text += f" · {failed} failed"
        self.status.config(text=text)

        if converted and self.show_folder.get():
            seen = set()
            for path in converted:
                folder = os.path.dirname(path)
                if folder in seen:
                    continue
                seen.add(folder)
                try:
                    show_in_folder(path)
                except Exception as e:
                    self.status.config(text=f"Can't open folder: {e}")

        if converted and self.open_after.get():
            for path in converted:
                try:
                    open_with_default_app(path)
                except Exception as e:
                    self.status.config(text=f"Can't open file: {e}")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
        except Exception:
            pass

    root = tk.Tk()
    App(root)
    root.mainloop()