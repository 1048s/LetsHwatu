import socket
import threading
import json
import random
import string

HOST = '0.0.0.0'
PORT = 9999

GWANG, YEOL, TTI, PI = "광", "열끗", "띠", "피"
TYPE_ORDER = {GWANG: 0, YEOL: 1, TTI: 2, PI: 3}

CARD_DATA = [
    (1,  GWANG, "송학",  False), (1,  TTI,  "홍단", False),
    (1,  PI,    "",      False), (1,  PI,   "",     False),
    (2,  YEOL,  "매조",  False), (2,  TTI,  "홍단", False),
    (2,  PI,    "",      False), (2,  PI,   "",     False),
    (3,  GWANG, "벚꽃",  False), (3,  TTI,  "홍단", False),
    (3,  PI,    "",      False), (3,  PI,   "",     False),
    (4,  YEOL,  "흑싸리",False), (4,  TTI,  "초단", False),
    (4,  PI,    "",      False), (4,  PI,   "",     False),
    (5,  YEOL,  "난초",  False), (5,  TTI,  "초단", False),
    (5,  PI,    "",      False), (5,  PI,   "",     False),
    (6,  YEOL,  "모란",  False), (6,  TTI,  "청단", False),
    (6,  PI,    "",      False), (6,  PI,   "",     False),
    (7,  YEOL,  "홍싸리",False), (7,  TTI,  "초단", False),
    (7,  PI,    "",      False), (7,  PI,   "",     False),
    (8,  GWANG, "공산",  False), (8,  YEOL, "공산", False),
    (8,  PI,    "",      False), (8,  PI,   "",     False),
    (9,  YEOL,  "국화",  False), (9,  TTI,  "청단", False),
    (9,  PI,    "",      False), (9,  PI,   "",     False),
    (10, YEOL,  "단풍",  False), (10, TTI,  "청단", False),
    (10, PI,    "",      False), (10, PI,   "",     False),
    (11, GWANG, "오동",  False), (11, PI,   "",     True),
    (11, PI,    "",      False), (11, PI,   "",     False),
    (12, GWANG, "비",    False), (12, YEOL, "비",   False),
    (12, PI,    "",      True),  (12, PI,   "",     False),
]


class Card:
    def __init__(self, month, ctype, name, is_double_pi=False):
        self.month = month
        self.ctype = ctype
        self.name = name
        self.is_double_pi = is_double_pi

    @property
    def pi_value(self):
        if self.ctype == PI:
            return 2 if self.is_double_pi else 1
        return 0

    def __repr__(self):
        return f"<{self.month}월 {self.ctype}>"


def card_sort_key(c):
    return (c.month, TYPE_ORDER[c.ctype], c.is_double_pi)


def card_to_dict(c):
    return {
        'month': c.month, 'ctype': c.ctype,
        'name': c.name, 'is_double_pi': c.is_double_pi,
    }


def calculate_score(cards):
    gwang_cards = [c for c in cards if c.ctype == GWANG]
    has_bi = any(c.month == 12 for c in gwang_cards)
    gwang = len(gwang_cards)
    yeol = sum(1 for c in cards if c.ctype == YEOL)
    tti  = sum(1 for c in cards if c.ctype == TTI)
    pi   = sum(c.pi_value for c in cards if c.ctype == PI)

    score = 0
    if gwang >= 5:   score += 15
    elif gwang == 4: score += 4
    elif gwang == 3: score += 2 if has_bi else 3
    if yeol >= 5: score += yeol - 4
    if tti  >= 5: score += tti - 4
    if pi   >= 10: score += pi - 9
    return score


# ============ 게임 상태 (서버 권위) ============
class RoomGame:
    def __init__(self, names):
        self.names = list(names)
        self.deck = [Card(*d) for d in CARD_DATA]
        random.shuffle(self.deck)

        self.hands = [[], []]
        self.collected = [[], []]
        self.table = []

        for _ in range(10):
            self.hands[0].append(self.deck.pop())
            self.hands[1].append(self.deck.pop())
        for _ in range(8):
            self.table.append(self.deck.pop())

        self.current = 0
        self.turn_state = "select_hand"
        self.pending_card = None
        self.pending_matches = []
        self.pending_drawn = None
        self.message = f"{self.names[0]}님의 차례입니다."
        self.phase = "playing"
        self._sort_all()

    def _sort_all(self):
        for h in self.hands:
            h.sort(key=card_sort_key)
        self.table.sort(key=card_sort_key)

    def find_matches(self, card, pool):
        return [c for c in pool if c.month == card.month]

    def play_hand(self, player_idx, card_idx):
        if self.phase != "playing":
            return False, "게임이 종료되었습니다"
        if player_idx != self.current:
            return False, "당신의 차례가 아닙니다"
        if self.turn_state != "select_hand":
            return False, "카드 선택 대기 중입니다"

        self._sort_all()
        hand = self.hands[player_idx]
        if not (0 <= card_idx < len(hand)):
            return False, "잘못된 카드 인덱스"

        card = hand.pop(card_idx)
        matches = self.find_matches(card, self.table)

        if len(matches) == 0:
            self.table.append(card)
            self.message = f"{self.names[player_idx]}: {card} → 매칭 없음"
            self._draw_and_resolve()
        elif len(matches) == 1:
            self.table.remove(matches[0])
            self.collected[player_idx].extend([matches[0], card])
            self.message = f"{self.names[player_idx]}: {card} ↔ {matches[0]} 획득"
            self._draw_and_resolve()
        else:
            self.pending_card = card
            self.pending_matches = matches
            self.turn_state = "select_table"
            self.message = f"{self.names[player_idx]}: 매칭할 카드를 선택하세요"
        return True, None

    def select_table(self, player_idx, card_idx):
        if player_idx != self.current:
            return False, "당신의 차례가 아닙니다"
        if self.turn_state not in ("select_table", "select_table_drawn"):
            return False, "지금은 테이블 선택 단계가 아닙니다"

        self._sort_all()
        if not (0 <= card_idx < len(self.table)):
            return False, "잘못된 테이블 인덱스"
        target = self.table[card_idx]
        if target not in self.pending_matches:
            return False, "매칭되지 않는 카드입니다"

        if self.turn_state == "select_table":
            card = self.pending_card
            self.table.remove(target)
            self.collected[player_idx].extend([target, card])
            self.pending_card = None
            self.pending_matches = []
            self.message = f"{self.names[player_idx]}: {card} ↔ {target} 획득"
            self._draw_and_resolve()
        else: # select_table_drawn
            card = self.pending_drawn
            self.table.remove(target)
            self.collected[player_idx].extend([target, card])
            self.pending_drawn = None
            self.pending_matches = []
            self.message += f" / 뒤집은 {card} ↔ {target} 획득"
            self._end_turn()
        return True, None

    def _draw_and_resolve(self):
        if not self.deck:
            self._end_turn()
            return
        drawn = self.deck.pop()
        matches = self.find_matches(drawn, self.table)
        if len(matches) == 0:
            self.table.append(drawn)
            self.message += f" / 뒤집은 {drawn}: 매칭 없음"
        elif len(matches) == 1:
            self.table.remove(matches[0])
            self.collected[self.current].extend([matches[0], drawn])
            self.message += f" / 뒤집은 {drawn} ↔ {matches[0]} 획득"
            self._end_turn()
        else:
            self.pending_drawn = drawn
            self.pending_matches = matches
            self.turn_state = "select_table_drawn"
            self.message += f" / 뒤집은 {drawn}: 매칭할 카드를 선택하세요"

    def _end_turn(self):
        self._sort_all()
        if not self.hands[0] and not self.hands[1]:
            self.phase = "result"
            return
        self.current = 1 - self.current
        self.turn_state = "select_hand"
        self.message = f"{self.names[self.current]}님의 차례입니다."

    def serialize_for(self, me):
        self._sort_all()
        opp = 1 - me
        pending_indices = []
        if self.current == me and self.turn_state in ("select_table", "select_table_drawn"):
            pending_indices = [i for i, c in enumerate(self.table)
                               if c in self.pending_matches]
        return {
            'my_hand': [card_to_dict(c) for c in self.hands[me]],
            'my_collected': [card_to_dict(c) for c in self.collected[me]],
            'opp_collected': [card_to_dict(c) for c in self.collected[opp]],
            'opp_hand_count': len(self.hands[opp]),
            'table': [card_to_dict(c) for c in self.table],
            'deck_count': len(self.deck),
            'is_my_turn': self.current == me,
            'turn_state': self.turn_state,
            'pending_match_indices': pending_indices,
            'my_score': calculate_score(self.collected[me]),
            'opp_score': calculate_score(self.collected[opp]),
            'phase': self.phase,
            'message': self.message,
            'names': list(self.names),
        }


# ============ 방 ============
class Room:
    def __init__(self, code):
        self.code = code
        self.clients = []     # ClientHandler 리스트 (최대 2)
        self.game = None

    def is_full(self):
        return len(self.clients) >= 2

    def try_start(self):
        if self.game is not None:
            return
        if len(self.clients) < 2:
            return
        names = [c.name for c in self.clients]
        self.game = RoomGame(names)
        for idx, c in enumerate(self.clients):
            c.send({'type': 'game_start', 'your_idx': idx, 'names': names})
        self.broadcast_state()

    def broadcast_state(self):
        if not self.game:
            return
        for idx, c in enumerate(self.clients):
            c.send({
                'type': 'state',
                'your_idx': idx,
                'state': self.game.serialize_for(idx),
            })

    def check_end(self):
        if not self.game or self.game.phase != "result":
            return
        scores = [calculate_score(self.game.collected[i]) for i in range(2)]
        winner = 0 if scores[0] > scores[1] else (1 if scores[1] > scores[0] else -1)
        for c in self.clients:
            c.send({'type': 'game_over', 'scores': scores, 'winner': winner,
                    'names': self.game.names})


# ============ 클라이언트 핸들러 ============
class ClientHandler(threading.Thread):
    def __init__(self, conn, addr, server):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.server = server
        self.name = None
        self.room = None
        self.player_idx = -1
        self.send_lock = threading.Lock()
        self.alive = True

    def send(self, msg):
        with self.send_lock:
            try:
                self.conn.sendall(
                    (json.dumps(msg, ensure_ascii=False) + "\n").encode('utf-8')
                )
            except Exception:
                self.alive = False

    def run(self):
        buf = b""
        try:
            while self.alive:
                data = self.conn.recv(8192)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode('utf-8'))
                        self.handle(msg)
                    except Exception as e:
                        self.send({'type': 'error', 'msg': f'프로토콜 오류: {e}'})
        except Exception:
            pass
        finally:
            self.cleanup()

    def handle(self, msg):
        cmd = msg.get('cmd')
        if cmd == 'create_room':
            self.name = (msg.get('name') or 'Player').strip()[:16]
            if self.room:
                return
            room = self.server.create_room()
            room.clients.append(self)
            self.room = room
            self.player_idx = 0
            self.send({'type': 'room_created', 'code': room.code, 'your_idx': 0})
            self.send({'type': 'waiting', 'msg': '상대방 대기 중...'})
            room.try_start()

        elif cmd == 'join_room':
            if self.room:
                return
            code = (msg.get('code') or '').strip().upper()
            self.name = (msg.get('name') or 'Player').strip()[:16]
            room = self.server.get_room(code)
            if not room:
                self.send({'type': 'error', 'msg': '방을 찾을 수 없습니다'})
                return
            if room.is_full():
                self.send({'type': 'error', 'msg': '방이 가득 찼습니다'})
                return
            room.clients.append(self)
            self.room = room
            self.player_idx = len(room.clients) - 1
            self.send({'type': 'room_joined', 'code': room.code,
                       'your_idx': self.player_idx})
            room.try_start()

        elif cmd == 'play_hand':
            if self.room and self.room.game:
                ok, err = self.room.game.play_hand(
                    self.player_idx, int(msg.get('card_idx', -1)))
                if not ok:
                    self.send({'type': 'error', 'msg': err})
                self.room.broadcast_state()
                self.room.check_end()

        elif cmd == 'select_table':
            if self.room and self.room.game:
                ok, err = self.room.game.select_table(
                    self.player_idx, int(msg.get('card_idx', -1)))
                if not ok:
                    self.send({'type': 'error', 'msg': err})
                self.room.broadcast_state()
                self.room.check_end()

        elif cmd == 'restart':
            if self.room and self.room.game and self.room.game.phase == 'result':
                names = [c.name for c in self.room.clients]
                if len(names) == 2:
                    self.room.game = RoomGame(names)
                    self.room.broadcast_state()

    def cleanup(self):
        self.alive = False
        try:
            self.conn.close()
        except Exception:
            pass
        if self.room:
            if self in self.room.clients:
                self.room.clients.remove(self)
            for c in list(self.room.clients):
                c.send({'type': 'error', 'msg': f'{self.name}님이 나갔습니다'})
            if not self.room.clients:
                self.server.remove_room(self.room.code)


# ============ 서버 ============
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.rooms = {}
        self.rooms_lock = threading.Lock()

    def gen_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
            if code not in self.rooms:
                return code

    def create_room(self):
        with self.rooms_lock:
            code = self.gen_code()
            room = Room(code)
            self.rooms[code] = room
            print(f"[+] 방 생성: {code} (총 {len(self.rooms)}개)")
            return room

    def get_room(self, code):
        return self.rooms.get(code)

    def remove_room(self, code):
        with self.rooms_lock:
            if code in self.rooms:
                del self.rooms[code]
                print(f"[-] 방 제거: {code} (총 {len(self.rooms)}개)")

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(20)
        print(f"서버 시작: {self.host}:{self.port}")
        try:
            while True:
                conn, addr = s.accept()
                print(f"[*] 접속: {addr}")
                ClientHandler(conn, addr, self).start()
        except KeyboardInterrupt:
            print("\n서버 종료")


if __name__ == '__main__':
    Server(HOST, PORT).run()