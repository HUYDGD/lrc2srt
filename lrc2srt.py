import ctypes
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askopenfilenames

# converter logic

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


# os helper

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


# user interface windows

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
SELECT = "#c7d2fe"

FONT = "Segoe UI" if sys.platform.startswith('win') else "Helvetica"


class App:
    def __init__(self, root):
        self.root = root
        self.srt_paths = {}  # tree item id -> srt path

        root.title("LRC2SRT Converter")
        root.geometry("560x760")
        root.minsize(480, 500)
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

        s.configure("Secondary.TButton", background=CARD, foreground=TEXT,
                    font=(FONT, 10), padding=(12, 8), bordercolor=BORDER,
                    lightcolor=CARD, darkcolor=CARD, focusthickness=0)
        s.map("Secondary.TButton",
              background=[("disabled", BG), ("pressed", BORDER), ("active", "#eef2ff")],
              foreground=[("disabled", "#9ca3af")])

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
        s.map("Treeview",
              background=[("selected", SELECT)],
              foreground=[("selected", TEXT)])

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
        results.pack(fill="both", expand=True, pady=(16, 8))

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

        # Interaction: selection, double-click, Enter, right-click
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_buttons())
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", lambda e: self.show_selected())
        right_click = "<Button-2>" if sys.platform == "darwin" else "<Button-3>"
        self.tree.bind(right_click, self.on_right_click)

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Show in folder", command=self.show_selected)
        self.menu.add_command(label="Open file", command=self.open_selected)

        # Empty-state hint (hidden after the first conversion)
        self.hint = tk.Label(results, bg=CARD, fg=MUTED, font=(FONT, 10),
                             text="Converted files will appear here.\n"
                                  "Select a row, then use the buttons below.")
        self.hint.place(relx=0.5, rely=0.5, anchor="center")

        # Row actions
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 12))
        self.btn_show = ttk.Button(actions, text="Show in folder",
                                   style="Secondary.TButton",
                                   command=self.show_selected, cursor="hand2")
        self.btn_show.pack(side="left", padx=(0, 8))
        self.btn_open = ttk.Button(actions, text="Open file",
                                   style="Secondary.TButton",
                                   command=self.open_selected, cursor="hand2")
        self.btn_open.pack(side="left")
        self.update_buttons()

        # Options card
        options = ttk.Frame(outer, style="Card.TFrame", padding=(16, 12))
        options.pack(fill="x")
        ttk.Label(options, text="After Converting", style="CardTitle.TLabel").pack(
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

    # ----- row interaction -----

    def selected_path(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.srt_paths.get(sel[0])

    def update_buttons(self):
        state = "!disabled" if self.selected_path() else "disabled"
        self.btn_show.state([state])
        self.btn_open.state([state])

    def show_selected(self):
        path = self.selected_path()
        if not path:
            return
        if not os.path.exists(path):
            self.status.config(text="File no longer exists.")
            return
        try:
            show_in_folder(path)
        except Exception as e:
            self.status.config(text=f"Can't open folder: {e}")

    def open_selected(self):
        path = self.selected_path()
        if not path:
            return
        if not os.path.exists(path):
            self.status.config(text="File no longer exists.")
            return
        try:
            open_with_default_app(path)
        except Exception as e:
            self.status.config(text=f"Can't open file: {e}")

    def on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.show_selected()

    def on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            if self.selected_path():
                self.menu.tk_popup(event.x_root, event.y_root)

    # ----- conversion -----

    def convert(self):
        files = askopenfilenames(
            parent=self.root,
            title="Select LRC file(s)",
            filetypes=[("LRC files", "*.lrc"), ("All files", "*.*")],
        )
        if not files:
            return

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

        # Pre-select the first converted row so the buttons are ready to use
        if self.srt_paths:
            first = next(iter(self.srt_paths))
            self.tree.selection_set(first)
            self.tree.focus(first)
        self.update_buttons()

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
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    App(root)
    root.mainloop()