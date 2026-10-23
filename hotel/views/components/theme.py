"""Design tokens and canvas illustrations recreated from the original web UI."""
from __future__ import annotations

import tkinter as tk

NAVY = '#19334d'
DEEP = '#10273c'
SIDEBAR = '#173149'
SIDEBAR_HOVER = '#294b65'
GOLD = '#c9a36d'
GOLD_LIGHT = '#e8c28f'
INK = '#293847'
MUTED = '#75828f'
EDGE = '#e3eaf0'
BACKGROUND = '#f6f8fb'
WHITE = '#ffffff'
FONT = 'Segoe UI'


def text(parent, value, size=11, fg=INK, bg=WHITE, weight='normal', **kwargs):
    return tk.Label(parent, text=value, font=(FONT, size, weight), fg=fg,
                    bg=bg, **kwargs)


def brand(parent, *, on_dark=False, tagline='HOTEL MANAGEMENT'):
    """Original square G monogram + two-line GrandStay wordmark."""
    bg = SIDEBAR if on_dark else WHITE
    holder = tk.Frame(parent, bg=bg)
    icon = tk.Canvas(holder, width=42, height=42, bg=bg, highlightthickness=0)
    icon.pack(side='left', padx=(0, 11))
    icon.create_rectangle(1, 1, 41, 41, fill=GOLD if on_dark else NAVY, outline='')
    icon.create_text(21, 20, text='G', fill=NAVY if on_dark else WHITE,
                     font=('Georgia', 24, 'bold'))
    caption = tk.Frame(holder, bg=bg)
    caption.pack(side='left')
    text(caption, 'GrandStay', 20, WHITE if on_dark else NAVY, bg, 'bold').pack(anchor='w')
    tk.Label(caption, text=tagline, font=(FONT, 8, 'bold'), fg=GOLD,
             bg=bg).pack(anchor='w')
    return holder


def solid_button(parent, title, command, *, light=False, width=None):
    return tk.Button(parent, text=title, command=command, cursor='hand2',
        font=(FONT, 10, 'bold'), fg=NAVY if light else WHITE,
        bg=WHITE if light else NAVY, activebackground='#eaf3fa' if light else '#27547a',
        activeforeground=NAVY if light else WHITE, bd=0, relief='flat',
        padx=19, pady=12, width=width)


def _rgb(hex_color):
    return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))


def gradient(canvas, width, height, start, end, *, horizontal=False):
    a, b = _rgb(start), _rgb(end)
    steps = max(1, width if horizontal else height)
    # Fewer individual items keep resizing the desktop UI responsive.
    skip = max(1, steps // 260)
    for i in range(0, steps, skip):
        mix = i / max(1, steps - 1)
        color = '#%02x%02x%02x' % tuple(int(a[j] * (1 - mix) + b[j] * mix) for j in range(3))
        if horizontal:
            canvas.create_rectangle(i, 0, i + skip, height, fill=color, outline=color)
        else:
            canvas.create_rectangle(0, i, width, i + skip, fill=color, outline=color)


def hotel_art(canvas, width, height, *, room=False, caption=True):
    """Native vector reproduction of CSS hotel-art and room-art (no webview)."""
    canvas.delete('all')
    if room:
        gradient(canvas, width, height, '#b3c7d4', '#ede0c9', horizontal=True)
        canvas.create_rectangle(width*.66, height*.09, width*.91, height*.66,
                                fill='#729eae', outline='#f2ece3', width=13)
        canvas.create_oval(width*.08, height*.43, width*.22, height*.86,
                           fill='#b8a28e', outline='')
        canvas.create_rectangle(width*.23, height*.7, width*.89, height*.87,
                                fill='#fbf8f0', outline='#826b5a', width=5)
        canvas.create_rectangle(width*.28, height*.62, width*.48, height*.73,
                                fill='#ffffff', outline='')
        canvas.create_text(15, 13, anchor='nw', text='GRANDSTAY COLLECTION',
                           font=(FONT, 8, 'bold'), fill=NAVY)
        return
    gradient(canvas, width, height, '#b7d7e9', '#c6b091', horizontal=True)
    canvas.create_oval(width*.07, height*.1, width*.32, height*.42,
                       fill='#f7dfa5', outline='')
    canvas.create_rectangle(width*.28, height*.25, width*.81, height*1.05,
                            fill='#ecdfc8', outline='#d8c1a2', width=8)
    canvas.create_rectangle(width*.28, height*.26, width*.81, height*.32,
                            fill='#526c79', outline='')
    for row in range(3):
        for col in range(4):
            xx = width*(.33 + col*.115)
            yy = height*(.37 + row*.15)
            canvas.create_rectangle(xx, yy, xx+width*.072, yy+height*.09,
                                    fill='#6d9baa', outline='#c3ab8c', width=4)
    canvas.create_rectangle(width*.53, height*.82, width*.63, height*1.02,
                            fill='#5a7c83', outline='#bea587', width=5)
    canvas.create_text(width*.04, height*.89, text='✥', font=('Georgia', 68), fill='#3e6b64')
    canvas.create_text(width*.93, height*.89, text='✥', font=('Georgia', 68), fill='#3e6b64')
    if caption:
        canvas.create_rectangle(15, height-66, width*.57, height-12,
                                fill='#ffffff', outline='')
        canvas.create_text(27, height-51, anchor='nw', text='Không gian nghỉ dưỡng hiện đại',
                           font=(FONT, 10, 'bold'), fill=NAVY)
        canvas.create_text(27, height-29, anchor='nw', text='Trọn vẹn sự thoải mái',
                           font=(FONT, 9), fill=MUTED)
        canvas.create_text(width-18, 15, anchor='ne', text='WELCOME TO GRANDSTAY',
                           font=(FONT, 9, 'bold'), fill=NAVY)
