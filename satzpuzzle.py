#!/usr/bin/env python3
"""Satzpuzzle: Wörter per Drag & Drop in die richtige Reihenfolge bringen.

Aufruf: python satzpuzzle.py [saetze.txt]
Ohne Argument wird 'saetze.txt' neben dem Programm (bzw. im aktuellen
Verzeichnis) geladen. Jede Zeile der Datei ist ein Satz.
"""
import os
import random
import sys
import tkinter as tk
import unicodedata
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

DEFAULT_FILE = "saetze.txt"

BG = "#f3f5fb"
PANEL = "#e1e6f3"
POOL_BG = "#dfe5f4"
SLOT_FILL = "#ffffff"
SLOT_LINE = "#2b3556"
TEXT = "#1f2740"
MUTED = "#5b6585"
ACCENT = "#3b5bdb"
TOKEN_STYLES = {
    None: ("#4c6ef5", "#2f49b8"),
    "ok": ("#2f9e62", "#1d7044"),
    "bad": ("#d6454b", "#9c2227"),
}
SHADOW = "#b7c0da"


def rr_points(x1, y1, x2, y2, r):
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


def ui_font_family():
    families = set(tkfont.families())
    for name in ("Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"):
        if name in families:
            return name
    return tkfont.nametofont("TkDefaultFont").actual("family")


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def strip_punct(word):
    """Entfernt Satzzeichen am Anfang und Ende eines Wortes."""
    start, end = 0, len(word)
    while start < end and unicodedata.category(word[start]).startswith("P"):
        start += 1
    while end > start and unicodedata.category(word[end - 1]).startswith("P"):
        end -= 1
    return word[start:end]


def tokenize(sentence):
    tokens = (strip_punct(raw) for raw in sentence.split())
    return [t for t in tokens if t]


def load_sentences(path):
    """Liest eine Textdatei (ein Satz pro Zeile) als Liste von Token-Listen."""
    with open(path, "rb") as f:
        data = f.read()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    return [tokens for tokens in map(tokenize, text.splitlines()) if tokens]


def shuffled(tokens):
    """Mischt die Tokens zufällig, möglichst nicht in Originalreihenfolge."""
    result = list(tokens)
    for _ in range(50):
        random.shuffle(result)
        if result != tokens:
            break
    return result


class Board(tk.Canvas):
    """Ablagebereich mit Wörtern oben und Platzhaltern darunter."""

    PAD = 10
    GAP = 8
    TOKEN_H = 36

    def __init__(self, master, on_change):
        super().__init__(master, bg=BG, highlightthickness=0, cursor="arrow")
        self.on_change = on_change
        self.font = tkfont.Font(family=ui_font_family(), size=14)
        self.label_font = tkfont.Font(family=ui_font_family(), size=11)
        self.original = []
        self.items = []
        self.slots = []
        self.locked = False
        self.drag = None
        self.bind("<Configure>", lambda e: self.relayout())
        self.tag_bind("token", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("token", "<Leave>", lambda e: self.config(cursor="arrow"))
        self.tag_bind("token", "<ButtonPress-1>", self._press)
        self.tag_bind("token", "<B1-Motion>", self._motion)
        self.tag_bind("token", "<ButtonRelease-1>", self._release)

    # --- Aufbau -----------------------------------------------------------

    def set_tokens(self, tokens):
        self.original = list(tokens)
        self.locked = False
        self.delete("all")
        self.items = []
        for i, text in enumerate(shuffled(tokens)):
            tag = f"t{i}"
            shadow = self.create_polygon(rr_points(0, 0, 4, 4, 1), smooth=True,
                                         fill=SHADOW, outline="", tags=("token", tag))
            rect = self.create_polygon(rr_points(0, 0, 4, 4, 1), smooth=True, width=2,
                                       tags=("token", tag))
            label = self.create_text(0, 0, text=text, font=self.font, fill="white",
                                     tags=("token", tag))
            self.items.append({"text": text, "slot": None, "state": None,
                               "w": self.font.measure(text) + 32, "home": (0, 0),
                               "shadow": shadow, "rect": rect, "label": label})
        self.relayout()
        self.on_change()

    def relayout(self):
        self.delete("bg")
        if not self.items:
            return
        width = max(self.winfo_width(), 300)
        pad, gap, h = self.PAD, self.GAP, self.TOKEN_H

        self.create_text(pad + 4, pad, text="WÖRTER", anchor="nw", fill=MUTED,
                         font=self.label_font, tags="bg")
        top = pad + 28
        x, y = pad + 8, top + 8
        for it in self.items:
            if x + it["w"] > width - pad - 8 and x > pad + 8:
                x, y = pad + 8, y + h + gap
            it["home"] = (x, y)
            x += it["w"] + gap
        pool_bottom = y + h + 12
        self.create_polygon(rr_points(pad, top, width - pad, pool_bottom, 14),
                            smooth=True, fill=POOL_BG, outline="", tags="bg")

        self.create_text(pad + 4, pool_bottom + pad + 6, text="DEIN SATZ", anchor="nw",
                         fill=MUTED, font=self.label_font, tags="bg")
        slot_w = max(it["w"] for it in self.items)
        x, y = pad, pool_bottom + pad + 36
        self.slots = []
        for n in range(len(self.items)):
            if x + slot_w > width - pad and x > pad:
                x, y = pad, y + h + gap + 6
            self.slots.append((x, y, slot_w))
            self.create_polygon(rr_points(x, y, x + slot_w, y + h, 10), smooth=True,
                                fill=SLOT_FILL, outline=SLOT_LINE, dash=(6, 3), width=2,
                                tags="bg")
            self.create_text(x + slot_w / 2, y + h / 2, text=str(n + 1), fill=SLOT_LINE,
                             font=self.label_font, tags="bg")
            x += slot_w + gap

        self.tag_lower("bg")
        for i in range(len(self.items)):
            self._place(i)

    def _position(self, it):
        if it["slot"] is None:
            return it["home"]
        sx, sy, sw = self.slots[it["slot"]]
        return sx + (sw - it["w"]) / 2, sy

    def _place(self, i):
        it = self.items[i]
        x, y = self._position(it)
        fill, line = TOKEN_STYLES[it["state"]]
        self.itemconfigure(it["rect"], fill=fill, outline=line)
        self._move(it, x, y)

    def _move(self, it, x, y):
        w, h = it["w"], self.TOKEN_H
        self.coords(it["shadow"], *rr_points(x, y + 3, x + w, y + h + 3, 10))
        self.coords(it["rect"], *rr_points(x, y, x + w, y + h, 10))
        self.coords(it["label"], x + w / 2, y + h / 2)

    # --- Drag & Drop ------------------------------------------------------

    def _token_at_cursor(self):
        for tag in self.gettags("current"):
            if tag.startswith("t") and tag[1:].isdigit():
                return int(tag[1:])
        return None

    def _press(self, event):
        if self.locked:
            return
        i = self._token_at_cursor()
        if i is None:
            return
        self.clear_marks()
        it = self.items[i]
        x, y = self._position(it)
        self.drag = {"i": i, "dx": event.x - x, "dy": event.y - y}
        self.tag_raise(f"t{i}")

    def _motion(self, event):
        if not self.drag:
            return
        i = self.drag["i"]
        it = self.items[i]
        x, y = event.x - self.drag["dx"], event.y - self.drag["dy"]
        self._move(it, x, y)

    def _release(self, event):
        if not self.drag:
            return
        i = self.drag["i"]
        self.drag = None
        it = self.items[i]
        target = self._slot_at(event.x, event.y)
        origin = it["slot"]
        if target is not None:
            for other in self.items:
                if other is not it and other["slot"] == target:
                    other["slot"] = origin
            it["slot"] = target
        else:
            it["slot"] = None
        for k in range(len(self.items)):
            self._place(k)
        self.on_change()

    def _slot_at(self, px, py):
        for idx, (x, y, w) in enumerate(self.slots):
            if x <= px <= x + w and y <= py <= y + self.TOKEN_H:
                return idx
        # Etwas großzügiger: nächster Platzhalter, wenn der Cursor knapp daneben liegt
        best, best_d = None, 30
        for idx, (x, y, w) in enumerate(self.slots):
            d = abs(px - (x + w / 2)) + abs(py - (y + self.TOKEN_H / 2))
            if d < best_d:
                best, best_d = idx, d
        return best

    # --- Auswertung -------------------------------------------------------

    def is_complete(self):
        return bool(self.items) and all(it["slot"] is not None for it in self.items)

    def clear_marks(self):
        for k, it in enumerate(self.items):
            if it["state"] is not None:
                it["state"] = None
                self._place(k)

    def check(self):
        """Markiert richtige/falsche Wörter und liefert den Anteil richtiger (0..1)."""
        correct = 0
        for k, it in enumerate(self.items):
            ok = self.original[it["slot"]] == it["text"]
            it["state"] = "ok" if ok else "bad"
            correct += ok
            self._place(k)
        return correct / len(self.items)


class App(tk.Tk):
    def __init__(self, path=None):
        super().__init__()
        self.title("Satzpuzzle")
        self.geometry("900x560")
        self.minsize(560, 380)
        self.configure(bg=BG)

        self.sentences = []
        self.order = []
        self.index = 0
        self.attempts = 0
        self.solved = False
        self.random_order = tk.BooleanVar(value=False)

        self._build_menu()
        self._build_ui()

        path = path or self._find_default()
        if path:
            self.load(path)
        else:
            self.header.config(
                text=f"Keine '{DEFAULT_FILE}' gefunden. Bitte über Datei → Öffnen laden.")

    # --- UI ---------------------------------------------------------------

    def _build_menu(self):
        bar = tk.Menu(self)
        datei = tk.Menu(bar, tearoff=False)
        datei.add_command(label="Öffnen…", accelerator="Strg+O", command=self.open_dialog)
        datei.add_separator()
        datei.add_command(label="Beenden", command=self.destroy)
        bar.add_cascade(label="Datei", menu=datei)
        optionen = tk.Menu(bar, tearoff=False)
        optionen.add_checkbutton(label="Sätze in zufälliger Reihenfolge",
                                 variable=self.random_order, command=self.start)
        bar.add_cascade(label="Optionen", menu=optionen)
        self.config(menu=bar)
        self.bind("<Control-o>", lambda e: self.open_dialog())

    def _build_styles(self):
        family = ui_font_family()
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=(family, 11), padding=(16, 8), borderwidth=0,
                        background=PANEL, foreground=TEXT, focuscolor=PANEL)
        style.map("TButton", background=[("active", "#cfd7ee"), ("disabled", "#eceff7")],
                  foreground=[("disabled", "#a0a8c2")])
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=(family, 11, "bold"), focuscolor=ACCENT)
        style.map("Accent.TButton",
                  background=[("active", "#5473e8"), ("disabled", "#b9c4ee")],
                  foreground=[("disabled", "#eef1fc")])
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL, background=ACCENT,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT, thickness=14)
        style.configure("Done.Horizontal.TProgressbar", troughcolor=PANEL,
                        background="#2f9e62", borderwidth=0, lightcolor="#2f9e62",
                        darkcolor="#2f9e62", thickness=14)
        self.family = family

    def _build_ui(self):
        self._build_styles()
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=18, pady=(16, 4))
        tk.Label(top, text="Satzpuzzle", bg=BG, fg=TEXT,
                 font=(self.family, 20, "bold")).pack(side="left")
        self.header = tk.Label(top, text="", bg=BG, fg=MUTED, font=(self.family, 11),
                               anchor="e")
        self.header.pack(side="right")

        self.board = Board(self, self._board_changed)
        self.board.pack(fill="both", expand=True, padx=12, pady=4)

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=18, pady=(4, 16))
        self.progress = ttk.Progressbar(bottom, maximum=100, length=240)
        self.progress.pack(side="left")
        self.progress_label = tk.Label(bottom, text="", bg=BG, fg=MUTED,
                                       font=(self.family, 11), anchor="w")
        self.progress_label.pack(side="left", padx=12)
        self.submit = ttk.Button(bottom, text="Prüfen", style="Accent.TButton",
                                 command=self.on_submit, state="disabled")
        self.submit.pack(side="right")
        self.reshuffle = ttk.Button(bottom, text="Neu mischen", command=self.on_reshuffle)
        self.reshuffle.pack(side="right", padx=8)

    # --- Laden ------------------------------------------------------------

    @staticmethod
    def _find_default():
        for folder in (app_dir(), os.getcwd()):
            candidate = os.path.join(folder, DEFAULT_FILE)
            if os.path.isfile(candidate):
                return candidate
        return None

    def open_dialog(self):
        path = filedialog.askopenfilename(
            title="Satzdatei öffnen",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")])
        if path:
            self.load(path)

    def load(self, path):
        try:
            sentences = load_sentences(path)
        except OSError as e:
            messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden:\n{e}")
            return
        if not sentences:
            messagebox.showwarning("Leere Datei", "Die Datei enthält keine Sätze.")
            return
        self.sentences = sentences
        self.start()

    def start(self):
        if not self.sentences:
            return
        self.order = list(range(len(self.sentences)))
        if self.random_order.get():
            random.shuffle(self.order)
        self.index = 0
        self.attempts = 0
        self.show_sentence()

    def show_sentence(self):
        self.solved = False
        self.header.config(text=f"Satz {self.index + 1} von {len(self.order)}"
                                f"   (Versuche: {self.attempts})")
        self.progress["value"] = 0
        self.progress.config(style="Horizontal.TProgressbar")
        self.progress_label.config(text="", fg=MUTED)
        self.submit.config(text="Prüfen")
        self.board.set_tokens(self.sentences[self.order[self.index]])

    # --- Aktionen ---------------------------------------------------------

    def _board_changed(self):
        if self.solved:
            return
        self.submit.config(state="normal" if self.board.is_complete() else "disabled")

    def on_reshuffle(self):
        if self.sentences and not self.solved:
            self.board.set_tokens(self.sentences[self.order[self.index]])

    def on_submit(self):
        if self.solved:
            self.next_sentence()
            return
        if not self.board.is_complete():
            return
        self.attempts += 1
        share = self.board.check()
        percent = round(share * 100)
        self.progress["value"] = percent
        self.header.config(text=f"Satz {self.index + 1} von {len(self.order)}"
                                f"   (Versuche: {self.attempts})")
        if share == 1:
            self.solved = True
            self.board.locked = True
            self.progress.config(style="Done.Horizontal.TProgressbar")
            self.progress_label.config(text="100 % – Richtig!", fg="#1d7044")
            last = self.index == len(self.order) - 1
            self.submit.config(text="Fertig" if last else "Weiter ►", state="normal")
        else:
            self.progress_label.config(text=f"{percent} % richtig platziert – "
                                            "versuche es nochmal", fg=MUTED)

    def next_sentence(self):
        if self.index < len(self.order) - 1:
            self.index += 1
            self.show_sentence()
        elif messagebox.askyesno("Geschafft!", "Alle Sätze gelöst. Nochmal von vorn?"):
            self.start()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    App(path).mainloop()


if __name__ == "__main__":
    main()
