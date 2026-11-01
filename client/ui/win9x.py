"""Windows 9x classic look helpers for Tkinter."""
import os
import tkinter as tk

DESKTOP = '#008080'
FACE = '#C0C0C0'
HIGHLIGHT = '#FFFFFF'
LIGHT = '#DFDFDF'
SHADOW = '#808080'
DKSHADOW = '#000000'
CAPTION = '#000080'
CAPTION_TEXT = '#FFFFFF'
WINDOW = '#FFFFFF'
WINDOW_TEXT = '#000000'
INFO_BK = '#FFFFE1'
FELT = '#006666'

UI_DIR = os.path.dirname(os.path.abspath(__file__))


def ui_path(name):
    return os.path.join(UI_DIR, name)


def pick_font(root, size=9, bold=False):
    families = set(root.tk.call('font', 'families'))
    for candidate in ('Tahoma', 'MS Sans Serif', 'Microsoft Sans Serif',
                      'DejaVu Sans', 'Liberation Sans', 'Helvetica'):
        if candidate in families:
            return (candidate, size, 'bold' if bold else 'normal')
    return ('TkDefaultFont', size, 'bold' if bold else 'normal')


class Bevel(tk.Frame):
    """Two-pixel raised or sunken bevel around content."""

    def __init__(self, master, sunken=False, fill=FACE, padx=0, pady=0, **kw):
        outer_tl = SHADOW if sunken else HIGHLIGHT
        outer_br = HIGHLIGHT if sunken else DKSHADOW
        inner_tl = DKSHADOW if sunken else LIGHT
        inner_br = LIGHT if sunken else SHADOW

        super().__init__(master, bg=outer_br, bd=0, highlightthickness=0, **kw)
        mid = tk.Frame(self, bg=outer_tl, bd=0)
        mid.pack(fill='both', expand=True, padx=(0, 1), pady=(0, 1))
        inner = tk.Frame(mid, bg=inner_br, bd=0)
        inner.pack(fill='both', expand=True, padx=(1, 0), pady=(1, 0))
        self.body = tk.Frame(inner, bg=fill, bd=0)
        self.body.pack(fill='both', expand=True, padx=(0, 1), pady=(0, 1))
        self.content = tk.Frame(self.body, bg=fill, bd=0)
        self.content.pack(fill='both', expand=True, padx=padx, pady=pady)

    def set_sunken(self, sunken):
        mid = self.winfo_children()[0]
        inner = mid.winfo_children()[0]
        if sunken:
            self.configure(bg=HIGHLIGHT)
            mid.configure(bg=SHADOW)
            inner.configure(bg=LIGHT)
        else:
            self.configure(bg=DKSHADOW)
            mid.configure(bg=HIGHLIGHT)
            inner.configure(bg=SHADOW)


def make_button(parent, text, command=None, font=None, width=None):
    """Classic raised Win9x push-button (native Tk Button + face colors)."""
    btn = tk.Button(
        parent, text=text, command=command,
        font=font or ('TkDefaultFont', 9),
        bg=FACE, fg=WINDOW_TEXT,
        activebackground=FACE, activeforeground=WINDOW_TEXT,
        relief='raised', bd=2, highlightthickness=0,
        padx=10, pady=2, cursor='hand2',
        width=width or 0)
    return btn


class TitleBar(tk.Frame):
    def __init__(self, master, title='Untitled', font=None, icon_img=None,
                 on_close=None):
        super().__init__(master, bg=CAPTION, height=22)
        self.pack_propagate(False)
        self.configure(height=22)
        self._imgs = {}

        if icon_img is not None:
            ic = tk.Label(self, image=icon_img, bg=CAPTION, bd=0)
            ic.image = icon_img
            ic.pack(side='left', padx=(3, 2), pady=3)

        self.title_lbl = tk.Label(
            self, text=title, bg=CAPTION, fg=CAPTION_TEXT,
            font=font or ('TkDefaultFont', 9, 'bold'), anchor='w')
        self.title_lbl.pack(side='left', fill='x', expand=True, padx=2)

        btns = tk.Frame(self, bg=CAPTION)
        btns.pack(side='right', padx=2, pady=2)

        for name, path, cmd in (
            ('min', 'btn_min.gif', None),
            ('max', 'btn_max.gif', None),
            ('close', 'btn_close.gif', on_close),
        ):
            p = ui_path(path)
            if os.path.exists(p):
                img = tk.PhotoImage(file=p)
                self._imgs[name] = img
                b = tk.Label(btns, image=img, bg=CAPTION, bd=0,
                             cursor='hand2' if cmd else 'arrow')
                b.pack(side='left', padx=1)
                if cmd:
                    b.bind('<Button-1>', lambda e, c=cmd: c())

    def set_title(self, title):
        self.title_lbl.configure(text=title)


class GroupBox(tk.Frame):
    """Etched group box with a caption label."""

    def __init__(self, master, text='', font=None, fill=FACE, **kw):
        super().__init__(master, bg=fill, bd=0, **kw)
        # etched: dark then light
        outer = tk.Frame(self, bg=SHADOW, bd=0)
        outer.pack(fill='both', expand=True, padx=0, pady=(8, 0))
        mid = tk.Frame(outer, bg=HIGHLIGHT, bd=0)
        mid.pack(fill='both', expand=True, padx=(0, 1), pady=(0, 1))
        mid2 = tk.Frame(mid, bg=HIGHLIGHT, bd=0)
        mid2.pack(fill='both', expand=True, padx=(1, 0), pady=(1, 0))
        wrap = tk.Frame(mid2, bg=SHADOW, bd=0)
        wrap.pack(fill='both', expand=True, padx=(0, 1), pady=(0, 1))
        self.body = tk.Frame(wrap, bg=fill, bd=0)
        self.body.pack(fill='both', expand=True)

        self._label = tk.Label(
            self, text=f' {text} ', bg=fill, fg=WINDOW_TEXT,
            font=font or ('TkDefaultFont', 9))
        self._label.place(x=8, y=0)

    def set_text(self, text):
        self._label.configure(text=f' {text} ')


class WindowChrome(tk.Frame):
    """Black outer border + raised client + title bar."""

    def __init__(self, master, title='Untitled', font=None, icon_img=None,
                 on_close=None, client_bg=FACE):
        super().__init__(master, bg=DKSHADOW, bd=0, highlightthickness=0)
        raised = Bevel(self, sunken=False, fill=FACE)
        raised.pack(fill='both', expand=True, padx=1, pady=1)

        self.titlebar = TitleBar(
            raised.content, title=title, font=font,
            icon_img=icon_img, on_close=on_close)
        self.titlebar.pack(fill='x', padx=2, pady=(2, 0))

        self.client = tk.Frame(raised.content, bg=client_bg, bd=0)
        self.client.pack(fill='both', expand=True, padx=2, pady=2)


class StatusBar(tk.Frame):
    def __init__(self, master, font=None, **kw):
        super().__init__(master, bg=FACE, bd=0, **kw)
        self.cells = []
        self._font = font

    def set_cells(self, texts):
        for w in self.winfo_children():
            w.destroy()
        self.cells = []
        for i, t in enumerate(texts):
            cell = Bevel(self, sunken=True, fill=FACE, padx=6, pady=1)
            cell.pack(side='left', fill='both', expand=(i == 0),
                      padx=(0, 2), pady=1)
            lbl = tk.Label(
                cell.content, text=t, bg=FACE, fg=WINDOW_TEXT,
                font=self._font, anchor='w')
            lbl.pack(fill='x')
            self.cells.append(lbl)

    def set_text(self, index, text):
        if 0 <= index < len(self.cells):
            self.cells[index].configure(text=text)


def make_entry(parent, font=None, width=16, **kw):
    bevel = Bevel(parent, sunken=True, fill=WINDOW, padx=2, pady=2)
    entry = tk.Entry(
        bevel.content, font=font, width=width, bd=0, highlightthickness=0,
        bg=WINDOW, fg=WINDOW_TEXT, insertbackground=WINDOW_TEXT, **kw)
    entry.pack(fill='x')
    return bevel, entry
