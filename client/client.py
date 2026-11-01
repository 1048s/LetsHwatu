import os
import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox

from ui.sprite import SpriteManager
from ui import win9x as w9

HOST = '127.0.0.1'
PORT = 9999

GWANG, YEOL, TTI, PI = "광", "열끗", "띠", "피"

TYPE_COLORS = {
    GWANG: ('#FFD700', '#000000'),
    YEOL:  ('#C00000', '#FFFFFF'),
    TTI:   ('#000080', '#FFFFFF'),
    PI:    ('#808080', '#FFFFFF'),
}

sprite_mgr = None


# ---------- 카드 위젯 ----------
def make_big_card(parent, card, clickable=False, is_pending=False, command=None,
                  font=None):
    img = None
    if sprite_mgr:
        try:
            img = sprite_mgr.get_card_image(card)
        except Exception:
            pass

    face = '#FFFFCC' if is_pending else w9.FACE
    outer = w9.Bevel(parent, sunken=False, fill=face, padx=1, pady=1)
    if is_pending:
        outer.configure(bg=w9.DKSHADOW)

    if img:
        lbl = tk.Label(outer.content, image=img, bg=face,
                       cursor='hand2' if clickable else 'arrow')
    else:
        bg, fg = TYPE_COLORS.get(card['ctype'], ('#C0C0C0', '#000000'))
        name = card['name'] or ''
        if card.get('is_double_pi'):
            name = '쌍피'
        text = f"{card['month']}월\n{card['ctype']}"
        if name and name != card['ctype']:
            text += f"\n{name}"
        lbl = tk.Label(
            outer.content, text=text, bg=bg, fg=fg, width=6, height=4,
            font=font or ('TkDefaultFont', 9, 'bold'),
            cursor='hand2' if clickable else 'arrow', bd=0)
    lbl.pack(fill='both', expand=True)

    if clickable and command:
        for w in (lbl, outer, outer.content, outer.body):
            w.bind('<Button-1>', lambda e, c=command: c())
    return outer


def make_small_card(parent, card, font=None):
    bg, fg = TYPE_COLORS.get(card['ctype'], ('#C0C0C0', '#000000'))
    text = f"{card['month']}{card['ctype'][0]}"
    if card['ctype'] == PI and card.get('is_double_pi'):
        text = f"{card['month']}쌍"
    bevel = w9.Bevel(parent, sunken=False, fill=bg)
    lbl = tk.Label(
        bevel.content, text=text, bg=bg, fg=fg, width=3, height=1,
        font=font or ('TkDefaultFont', 8, 'bold'), bd=0)
    lbl.pack()
    return bevel


# ---------- 앱 ----------
class GameApp:
    def __init__(self, root):
        self.root = root
        self.root.title('화투 (Go-Stop)')
        self.root.geometry('720x560')
        self.root.minsize(640, 480)
        self.root.configure(bg=w9.FACE)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)

        self.font = w9.pick_font(root, 9)
        self.font_b = w9.pick_font(root, 9, bold=True)
        self.font_sm = w9.pick_font(root, 8)
        self.font_hero = w9.pick_font(root, 12, bold=True)

        self.sock = None
        self.your_idx = -1
        self.state = None
        self.names = None
        self.alive = False
        self.room_code = None

        global sprite_mgr
        sprite_path = os.path.join(os.path.dirname(__file__), 'ui', 'hwatu.png')
        sprite_mgr = SpriteManager(sprite_path)

        self.lobby_frame = tk.Frame(root, bg=w9.FACE)
        self.game_frame = tk.Frame(root, bg=w9.FACE)
        self.build_lobby()
        self.lobby_frame.pack(fill='both', expand=True)

    # ---------- Lobby ----------
    def build_lobby(self):
        f = self.lobby_frame

        body = tk.Frame(f, bg=w9.FACE)
        body.pack(fill='both', expand=True, padx=12, pady=8)

        tk.Label(body, text='화투 — Go-Stop', font=self.font_hero,
                 bg=w9.FACE, fg=w9.CAPTION).pack(anchor='w', pady=(2, 6))

        g_player = w9.GroupBox(body, text='플레이어', font=self.font, fill=w9.FACE)
        g_player.pack(fill='x', pady=2)
        row = tk.Frame(g_player.body, bg=w9.FACE)
        row.pack(fill='x', padx=8, pady=6)
        tk.Label(row, text='이름:', font=self.font,
                 bg=w9.FACE, fg=w9.WINDOW_TEXT).pack(side='left')
        name_bev, self.name_entry = w9.make_entry(row, font=self.font, width=16)
        name_bev.pack(side='left', padx=6)

        g_room = w9.GroupBox(body, text='방', font=self.font, fill=w9.FACE)
        g_room.pack(fill='x', pady=4)
        room_body = tk.Frame(g_room.body, bg=w9.FACE)
        room_body.pack(fill='x', padx=8, pady=6)

        row1 = tk.Frame(room_body, bg=w9.FACE)
        row1.pack(fill='x')
        create_btn = w9.make_button(
            row1, '방 만들기', command=self.do_create,
            font=self.font_b, width=12)
        create_btn.pack(side='left')

        jf = tk.Frame(room_body, bg=w9.FACE)
        jf.pack(fill='x', pady=(6, 0))
        tk.Label(jf, text='방 코드:', font=self.font,
                 bg=w9.FACE, fg=w9.WINDOW_TEXT).pack(side='left')
        code_bev, self.code_entry = w9.make_entry(jf, font=self.font, width=8)
        code_bev.pack(side='left', padx=6)
        self.code_entry.bind('<Return>', lambda e: self.do_join())
        join_btn = w9.make_button(
            jf, '참가', command=self.do_join, font=self.font, width=6)
        join_btn.pack(side='left', padx=4)

        code_panel = w9.Bevel(body, sunken=True, fill=w9.WINDOW, padx=8, pady=4)
        code_panel.pack(fill='x', pady=(6, 2))
        code_row = tk.Frame(code_panel.content, bg=w9.WINDOW)
        code_row.pack(fill='x')
        tk.Label(code_row, text='방 코드', font=self.font,
                 bg=w9.WINDOW, fg=w9.SHADOW).pack(side='left')
        self.room_code_label = tk.Label(
            code_row, text='————',
            font=w9.pick_font(self.root, 16, bold=True),
            bg=w9.WINDOW, fg=w9.CAPTION)
        self.room_code_label.pack(side='left', padx=10)
        self.status_label = tk.Label(
            code_panel.content,
            text='방을 만들거나 참가하세요.',
            font=self.font_sm, bg=w9.WINDOW, fg=w9.WINDOW_TEXT,
            justify='left', anchor='w')
        self.status_label.pack(fill='x', pady=(2, 0))

        g_srv = w9.GroupBox(body, text='서버', font=self.font, fill=w9.FACE)
        g_srv.pack(fill='x', pady=4)
        sf = tk.Frame(g_srv.body, bg=w9.FACE)
        sf.pack(fill='x', padx=8, pady=6)
        tk.Label(sf, text='호스트:', font=self.font_sm,
                 bg=w9.FACE, fg=w9.WINDOW_TEXT).pack(side='left')
        host_bev, self.host_entry = w9.make_entry(sf, font=self.font_sm, width=14)
        self.host_entry.insert(0, HOST)
        host_bev.pack(side='left', padx=4)
        tk.Label(sf, text='포트:', font=self.font_sm,
                 bg=w9.FACE, fg=w9.WINDOW_TEXT).pack(side='left', padx=(8, 0))
        port_bev, self.port_entry = w9.make_entry(sf, font=self.font_sm, width=6)
        self.port_entry.insert(0, str(PORT))
        port_bev.pack(side='left', padx=4)

        sb = w9.StatusBar(f, font=self.font_sm)
        sb.pack(fill='x', side='bottom', padx=1, pady=1)
        sb.set_cells(['준비', '2인 대전', ''])
        self.lobby_status = sb

    def _set_lobby_status(self, text, code=None):
        self.status_label.config(text=text)
        if code:
            self.room_code = code
            self.room_code_label.config(text=code)
            self.code_entry.delete(0, 'end')
            self.code_entry.insert(0, code)
            self.lobby_status.set_cells([f'방 코드: {code}', '상대 대기 중', ''])
            self.root.title(f'화투 (Go-Stop) — 방 {code}')

    def do_create(self):
        name = self.name_entry.get().strip() or 'Player'
        if not self.connect():
            return
        self.send({'cmd': 'create_room', 'name': name})

    def do_join(self):
        name = self.name_entry.get().strip() or 'Player'
        code = self.code_entry.get().strip().upper()
        if not code:
            messagebox.showwarning('알림', '방 코드를 입력하세요')
            return
        if not self.connect():
            return
        self.send({'cmd': 'join_room', 'name': name, 'code': code})

    # ---------- Network ----------
    def connect(self):
        if self.sock:
            return True
        try:
            host = self.host_entry.get().strip() or HOST
            port = int(self.port_entry.get().strip() or PORT)
            # timeout only for the initial handshake — clear it after connect,
            # otherwise recv() drops the socket ~5s while waiting for a partner
            self.sock = socket.create_connection((host, port), timeout=5)
            self.sock.settimeout(None)
            self.alive = True
            threading.Thread(target=self.recv_loop, daemon=True).start()
            return True
        except Exception as e:
            messagebox.showerror('연결 실패', f'서버에 연결할 수 없습니다:\n{e}')
            self.sock = None
            return False

    def send(self, msg):
        if not self.sock:
            return
        try:
            self.sock.sendall((json.dumps(msg, ensure_ascii=False) + '\n').encode('utf-8'))
        except Exception as e:
            messagebox.showerror('전송 오류', str(e))

    def recv_loop(self):
        buf = b''
        sock = self.sock
        try:
            while self.alive and sock:
                try:
                    data = sock.recv(8192)
                except socket.timeout:
                    continue
                if not data:
                    break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode('utf-8'))
                        self.root.after(0, self.handle_message, msg)
                    except Exception as e:
                        print('parse error:', e)
        except OSError as e:
            if self.alive:
                print('recv_loop ended:', e)
        finally:
            self.alive = False
            self.root.after(0, self.on_disconnect)

    def on_disconnect(self):
        if self.state is None:
            self.status_label.config(text='서버 연결이 끊어졌습니다.')
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

    def handle_message(self, msg):
        t = msg.get('type')
        if t == 'room_created':
            self.your_idx = msg['your_idx']
            code = msg['code']
            self._set_lobby_status(
                f'방 코드: {code}  —  상대 대기 중...', code=code)
        elif t == 'room_joined':
            self.your_idx = msg['your_idx']
            self.room_code = msg.get('code')
            if self.room_code:
                self._set_lobby_status(
                    f'방 {self.room_code}에 참가했습니다. 게임 시작 대기...',
                    code=self.room_code)
        elif t == 'waiting':
            # Keep room code visible; append waiting text if we have a code
            if self.room_code:
                self.status_label.config(
                    text=f'방 코드: {self.room_code}  —  {msg["msg"]}')
            else:
                self.status_label.config(text=msg['msg'])
        elif t == 'game_start':
            self.your_idx = msg['your_idx']
            self.names = msg['names']
            self.show_game()
        elif t == 'state':
            self.state = msg['state']
            self.render_game()
        elif t == 'game_over':
            self.show_game_over(msg)
        elif t == 'error':
            if self.state is None:
                messagebox.showwarning('알림', msg['msg'])
            else:
                self.msg_label.config(
                    text=f'! {msg["msg"]}', fg='#800000', bg=w9.INFO_BK)

    # ---------- Game UI ----------
    def show_game(self):
        self.lobby_frame.pack_forget()
        if not self.game_frame.winfo_children():
            self.build_game()
        self.game_frame.pack(fill='both', expand=True)
        if self.names and len(self.names) == 2:
            self.root.title(
                f'화투 — {self.names[self.your_idx]} vs '
                f'{self.names[1 - self.your_idx]}')

    def build_game(self):
        f = self.game_frame

        msg_wrap = w9.Bevel(f, sunken=True, fill=w9.INFO_BK, padx=6, pady=2)
        msg_wrap.pack(fill='x', padx=4, pady=(4, 1))
        self.msg_label = tk.Label(
            msg_wrap.content, text='', bg=w9.INFO_BK, fg=w9.WINDOW_TEXT,
            font=self.font_b, anchor='w')
        self.msg_label.pack(fill='x')

        self.opp_frame = w9.GroupBox(f, text='상대', font=self.font, fill=w9.FACE)
        self.opp_frame.pack(fill='x', padx=4, pady=1)
        self.opp_header = tk.Label(
            self.opp_frame.body, text='', bg=w9.FACE, fg=w9.WINDOW_TEXT,
            font=self.font_sm, anchor='w')
        self.opp_header.pack(fill='x', padx=6, pady=(4, 0))
        self.opp_cards = tk.Frame(self.opp_frame.body, bg=w9.FACE)
        self.opp_cards.pack(fill='x', padx=6, pady=(0, 4))

        self.table_frame = w9.GroupBox(f, text='테이블', font=self.font, fill=w9.FACE)
        self.table_frame.pack(fill='x', padx=4, pady=1)
        felt = w9.Bevel(self.table_frame.body, sunken=True, fill=w9.FELT,
                        padx=4, pady=4)
        felt.pack(fill='x', padx=4, pady=4)
        self.table_inner = tk.Frame(felt.content, bg=w9.FELT)
        self.table_inner.pack()

        self.mycol_frame = w9.GroupBox(
            f, text='내 획득 카드', font=self.font, fill=w9.FACE)
        self.mycol_frame.pack(fill='x', padx=4, pady=1)
        self.mycol_inner = tk.Frame(self.mycol_frame.body, bg=w9.FACE)
        self.mycol_inner.pack(fill='x', padx=6, pady=4)

        self.hand_frame = w9.GroupBox(f, text='내 패', font=self.font, fill=w9.FACE)
        self.hand_frame.pack(fill='x', padx=4, pady=1)
        self.hand_inner = tk.Frame(self.hand_frame.body, bg=w9.FACE)
        self.hand_inner.pack(fill='x', padx=6, pady=4)

        self.restart_row = tk.Frame(f, bg=w9.FACE)
        self.restart_btn = w9.make_button(
            self.restart_row, '다시 시작', command=self.do_restart,
            font=self.font_b, width=12)
        self.restart_btn.pack(pady=2)

        self.game_status = w9.StatusBar(f, font=self.font_sm)
        self.game_status.pack(fill='x', side='bottom', padx=1, pady=1)
        self.game_status.set_cells(['대기', '점수 0', '덱 —'])

    def render_game(self):
        s = self.state
        if not s:
            return
        names = s.get('names', ['나', '상대'])
        me = self.your_idx
        opp = 1 - me

        self.opp_frame.set_text(f'상대 — {names[opp]}')
        self.opp_header.config(
            text=f"점수: {s['opp_score']}    패: {s['opp_hand_count']}장    "
                 f"획득: {len(s['opp_collected'])}장")

        for w in self.opp_cards.winfo_children():
            w.destroy()
        for c in s['opp_collected']:
            make_small_card(self.opp_cards, c, font=self.font_sm).pack(
                side='left', padx=1, pady=1)

        self.msg_label.config(text=s['message'], fg=w9.WINDOW_TEXT, bg=w9.INFO_BK)

        turn = '내 차례' if s['is_my_turn'] else '상대 차례'
        self.game_status.set_cells([
            turn,
            f"내 점수 {s['my_score']}",
            f"덱 {s['deck_count']}장",
        ])
        self.root.title(f'화투 — {names[me]} vs {names[opp]}')

        for w in self.table_inner.winfo_children():
            w.destroy()
        pending = set(s.get('pending_match_indices', []))
        can_sel = s['is_my_turn'] and s['turn_state'] in (
            'select_table', 'select_table_drawn')
        for i, c in enumerate(s['table']):
            clickable = can_sel and i in pending
            w = make_big_card(
                self.table_inner, c,
                clickable=clickable,
                is_pending=(i in pending),
                command=lambda idx=i: self.on_select_table(idx),
                font=self.font_b)
            w.pack(side='left', padx=1, pady=1)

        for w in self.mycol_inner.winfo_children():
            w.destroy()
        for c in s['my_collected']:
            make_small_card(self.mycol_inner, c, font=self.font_sm).pack(
                side='left', padx=1, pady=1)

        for w in self.hand_inner.winfo_children():
            w.destroy()
        can_play = (s['is_my_turn'] and s['turn_state'] == 'select_hand'
                    and s['phase'] == 'playing')
        for i, c in enumerate(s['my_hand']):
            w = make_big_card(
                self.hand_inner, c,
                clickable=can_play,
                command=lambda idx=i: self.on_play_hand(idx),
                font=self.font_b)
            w.pack(side='left', padx=1, pady=1)

        if s['phase'] == 'result':
            self.restart_row.pack(pady=6)
        else:
            self.restart_row.pack_forget()

    def on_play_hand(self, idx):
        self.send({'cmd': 'play_hand', 'card_idx': idx})

    def on_select_table(self, idx):
        self.send({'cmd': 'select_table', 'card_idx': idx})

    def show_game_over(self, msg):
        scores = msg['scores']
        names = msg['names']
        winner = msg['winner']
        if winner == -1:
            body = f"무승부\n\n{names[0]}: {scores[0]}점\n{names[1]}: {scores[1]}점"
        else:
            body = f"{names[winner]}님 승리!\n\n" \
                   f"{names[0]}: {scores[0]}점\n{names[1]}: {scores[1]}점"
        messagebox.showinfo('게임 종료', body)
        self.restart_row.pack(pady=6)

    def do_restart(self):
        self.send({'cmd': 'restart'})
        self.restart_row.pack_forget()

    def on_close(self):
        self.alive = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    GameApp(root)
    root.mainloop()
