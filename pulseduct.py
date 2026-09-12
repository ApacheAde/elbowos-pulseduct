#!/usr/bin/env python3
"""PulseDuct — neon pipe-dream arcade for ElbowOS. Python 3 + pygame.
Click a tile (or tap) to rotate. Connect the source well to the sink.
RECORD=1 writes a 15s 1080x1920 autoplay reel.
"""
import os, sys, math, random, subprocess
import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "PULSEDUCT"
COLS, ROWS = 5, 7
CELL = 168
OX = (W - COLS * CELL) // 2
OY = 360
N, E, S, WW = 0, 1, 2, 3
DELTA = {N: (0, -1), E: (1, 0), S: (0, 1), WW: (-1, 0)}
OPP = {N: S, E: WW, S: N, WW: E}

# kind -> openings at rot 0
KINDS = {
    "I": (N, S),
    "L": (N, E),
    "T": (WW, N, E),
    "X": (N, E, S, WW),
}


def openings(kind, rot):
    return tuple((d + rot) % 4 for d in KINDS[kind])


def rotate_open(op, rot):
    return tuple((d + rot) % 4 for d in op)


class Tile:
    def __init__(self, kind, rot=0):
        self.kind = kind
        self.rot = rot % 4
        self.spin = 0.0
        self.hot = 0.0
        self.pulse = random.random() * 6.28

    def ports(self):
        extra = 1 if self.spin > 0.2 else 0
        return openings(self.kind, self.rot + extra)

    def kick(self):
        self.rot = (self.rot + 1) % 4
        self.spin = 1.0


class Game:
    def __init__(self):
        self.score = 0
        self.level = 1
        self.flash = 0.0
        self.flow_t = 0.0
        self.cursor = [2, 3]
        self.particles = []
        self.solved = False
        self.hint_cd = 0
        self.new_board()

    def new_board(self):
        self.tiles = [[Tile(random.choice(list(KINDS)), random.randint(0, 3))
                       for _ in range(COLS)] for _ in range(ROWS)]
        path = self._carve_path()
        for (c, r), kind, rot in path:
            self.tiles[r][c] = Tile(kind, rot)
        for _ in range(8 + self.level):
            r, c = random.randrange(ROWS), random.randrange(COLS)
            self.tiles[r][c].rot = (self.tiles[r][c].rot + random.randint(1, 3)) % 4
        self.solved = False
        self.particles.clear()
        self.src = (2, -1)
        self.dst = (2, ROWS)

    def _carve_path(self):
        c = 2
        path = []
        for r in range(ROWS):
            nxt = c if r == ROWS - 1 else max(0, min(COLS - 1, c + random.choice([-1, 0, 0, 1])))
            if nxt == c:
                path.append(((c, r), "I", 0))
            elif nxt > c:
                path.append(((c, r), "L", 1))
                path.append(((nxt, r), "L", 2))
                c = nxt
            else:
                path.append(((c, r), "L", 2))
                path.append(((nxt, r), "L", 1))
                c = nxt
        d = {}
        for item in path:
            d[item[0]] = item
        return list(d.values())

    def inb(self, c, r):
        return 0 <= c < COLS and 0 <= r < ROWS

    def connected(self):
        lit = set()
        q = [(2, 0, N)]
        seen = set()
        reached_sink = False
        while q:
            c, r, entered = q.pop(0)
            if not self.inb(c, r):
                continue
            key = (c, r, entered)
            if key in seen:
                continue
            seen.add(key)
            t = self.tiles[r][c]
            ports = t.ports()
            if entered not in ports:
                continue
            lit.add((c, r))
            t.hot = min(1.0, t.hot + 0.18)
            for d in ports:
                if d == entered:
                    continue
                dc, dr = DELTA[d]
                nc, nr = c + dc, r + dr
                if nr == ROWS and nc == 2 and d == S:
                    reached_sink = True
                if self.inb(nc, nr):
                    q.append((nc, nr, OPP[d]))
        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) not in lit:
                    self.tiles[r][c].hot *= 0.86
        return lit, reached_sink

    def tap(self, c, r):
        if self.inb(c, r):
            self.tiles[r][c].kick()
            self.cursor = [c, r]

    def autoplay(self, frame):
        if self.hint_cd > 0:
            self.hint_cd -= 1
        else:
            c = (self.cursor[0] + random.choice([-1, 0, 0, 1])) % COLS
            r = (self.cursor[1] + random.choice([-1, 0, 0, 1])) % ROWS
            self.tap(c, r)
            self.hint_cd = 8 + random.randint(0, 6)
        if frame % 11 == 0:
            self.spawn_plasma()

    def spawn_plasma(self):
        lit, _ = self.connected()
        if not lit:
            self.particles.append([OX + 2 * CELL + CELL / 2, OY - 40, 2, 4])
            return
        c, r = random.choice(list(lit))
        self.particles.append([
            OX + c * CELL + CELL / 2 + random.uniform(-12, 12),
            OY + r * CELL + CELL / 2 + random.uniform(-12, 12),
            random.uniform(-1.2, 1.2),
            random.uniform(-2.4, 0.6),
        ])

    def step(self):
        self.flow_t += 0.07
        self.flash = max(0.0, self.flash - 0.04)
        lit, sink = self.connected()
        if sink and not self.solved:
            self.solved = True
            self.score += 250 + 40 * len(lit)
            self.flash = 1.0
        if self.solved and self.flash <= 0.02:
            self.level += 1
            self.new_board()
        for trow in self.tiles:
            for t in trow:
                t.spin = max(0.0, t.spin - 0.12)
                t.pulse += 0.15
        alive = []
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.08
            if 0 < p[0] < W and 0 < p[1] < H - 80:
                alive.append(p)
        self.particles = alive[-90:]


def draw_bg(surf, g):
    surf.fill((8, 4, 22))
    for i in range(18):
        y = (i * 140 + int(g.flow_t * 28)) % (H + 140) - 70
        pygame.draw.line(surf, (28, 8, 48), (0, y), (W, y + 90), 18)
    pygame.draw.rect(surf, (14, 6, 36), (0, 0, W, 280))
    pygame.draw.rect(surf, (14, 6, 36), (0, H - 160, W, 160))


def draw_pipe(surf, x, y, kind, rot, hot, spin, pulse):
    cx, cy = x + CELL // 2, y + CELL // 2
    glow = int(40 + 180 * hot + 20 * math.sin(pulse))
    body = (36, 48, 78)
    rim = (90, 220, 255) if hot < 0.3 else (255, 70, 210)
    plasma = (255, min(255, 80 + glow), min(255, 40 + glow // 2))
    pygame.draw.rect(surf, (18, 12, 40), (x + 8, y + 8, CELL - 16, CELL - 16), border_radius=22)
    pygame.draw.rect(surf, rim, (x + 8, y + 8, CELL - 16, CELL - 16), 3, border_radius=22)
    ports = openings(kind, rot)
    thick = 28
    pygame.draw.circle(surf, body, (cx, cy), 26)
    if hot > 0.15:
        pygame.draw.circle(surf, plasma, (cx, cy), int(10 + 8 * hot + 3 * math.sin(pulse)))
    for d in ports:
        if d == N:
            pygame.draw.rect(surf, body, (cx - thick // 2, y + 10, thick, cy - y))
            if hot > 0.12:
                pygame.draw.rect(surf, plasma, (cx - 8, y + 16, 16, cy - y - 10))
        elif d == S:
            pygame.draw.rect(surf, body, (cx - thick // 2, cy, thick, y + CELL - 10 - cy))
            if hot > 0.12:
                pygame.draw.rect(surf, plasma, (cx - 8, cy, 16, y + CELL - 16 - cy))
        elif d == E:
            pygame.draw.rect(surf, body, (cx, cy - thick // 2, x + CELL - 10 - cx, thick))
            if hot > 0.12:
                pygame.draw.rect(surf, plasma, (cx, cy - 8, x + CELL - 16 - cx, 16))
        else:
            pygame.draw.rect(surf, body, (x + 10, cy - thick // 2, cx - x - 10, thick))
            if hot > 0.12:
                pygame.draw.rect(surf, plasma, (x + 16, cy - 8, cx - x - 16, 16))
    pygame.draw.circle(surf, rim, (cx, cy), 26, 3)
    if spin > 0:
        pygame.draw.circle(surf, (255, 230, 90), (cx, cy), int(30 + 10 * spin), 2)


def draw_hud(surf, font, big, g):
    title = big.render(TITLE, True, (255, 80, 200))
    surf.blit(title, title.get_rect(center=(W // 2, 86)))
    sub = font.render("x.com/ElbowOS", True, (120, 240, 255))
    surf.blit(sub, sub.get_rect(center=(W // 2, 150)))
    sc = font.render(f"SCORE  {g.score}", True, (255, 230, 90))
    lv = font.render(f"LEVEL  {g.level}", True, (180, 255, 160))
    surf.blit(sc, (64, 200))
    surf.blit(lv, (W - 64 - lv.get_width(), 200))
    pygame.draw.circle(surf, (255, 60, 180), (OX + 2 * CELL + CELL // 2, OY - 48), 28)
    pygame.draw.circle(surf, (255, 220, 80), (OX + 2 * CELL + CELL // 2, OY - 48), 14)
    pygame.draw.circle(surf, (60, 255, 200), (OX + 2 * CELL + CELL // 2, OY + ROWS * CELL + 48), 28)
    pygame.draw.circle(surf, (200, 255, 240), (OX + 2 * CELL + CELL // 2, OY + ROWS * CELL + 48), 14)
    hint = font.render("rotate tiles  ·  duct plasma to the sink", True, (160, 140, 220))
    surf.blit(hint, hint.get_rect(center=(W // 2, H - 80)))
    if g.flash > 0:
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((255, 70, 200, int(90 * g.flash)))
        surf.blit(veil, (0, 0))


def render(surf, fonts, g):
    font, big = fonts
    draw_bg(surf, g)
    for r in range(ROWS):
        for c in range(COLS):
            t = g.tiles[r][c]
            x, y = OX + c * CELL, OY + r * CELL
            draw_pipe(surf, x, y, t.kind, t.rot, t.hot, t.spin, t.pulse)
            if [c, r] == g.cursor:
                pygame.draw.rect(surf, (255, 240, 80), (x + 4, y + 4, CELL - 8, CELL - 8), 3, border_radius=18)
    for p in g.particles:
        pygame.draw.circle(surf, (255, 120, 230), (int(p[0]), int(p[1])), 6)
        pygame.draw.circle(surf, (255, 240, 180), (int(p[0]), int(p[1])), 3)
    draw_hud(surf, font, big, g)


def cell_at(pos):
    x, y = pos
    c = (x - OX) // CELL
    r = (y - OY) // CELL
    return int(c), int(r)


def record(surf, fonts, g):
    out = "/home/workdir/artifacts/PulseDuct_ElbowOS.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast", "-movflags", "+faststart", out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = FPS * 15
    for i in range(frames):
        g.autoplay(i)
        g.step()
        if i % 4 == 0:
            g.spawn_plasma()
        render(surf, fonts, g)
        payload = pygame.image.tostring(surf, "RGB")
        try:
            proc.stdin.write(payload)
        except BrokenPipeError:
            err = proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else ""
            raise RuntimeError("ffmpeg pipe broke:\n" + err)
    proc.stdin.close()
    rc = proc.wait()
    err = proc.stderr.read() if proc.stderr else b""
    if rc != 0:
        raise RuntimeError(err.decode("utf-8", "ignore")[-2000:])
    print("WROTE", out)
    return out


def play(surf, fonts, g, clock):
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    return
                if ev.key == pygame.K_LEFT:
                    g.cursor[0] = (g.cursor[0] - 1) % COLS
                if ev.key == pygame.K_RIGHT:
                    g.cursor[0] = (g.cursor[0] + 1) % COLS
                if ev.key == pygame.K_UP:
                    g.cursor[1] = (g.cursor[1] - 1) % ROWS
                if ev.key == pygame.K_DOWN:
                    g.cursor[1] = (g.cursor[1] + 1) % ROWS
                if ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    g.tap(*g.cursor)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                g.tap(*cell_at(ev.pos))
        g.step()
        render(surf, fonts, g)
        pygame.display.flip()
        clock.tick(FPS)


def main():
    record_mode = os.environ.get("RECORD", "0") == "1" or "--record" in sys.argv
    if record_mode:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    if record_mode:
        screen = pygame.Surface((W, H))
    else:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("PulseDuct — ElbowOS")
    fonts = (pygame.font.SysFont("DejaVu Sans", 36, bold=True),
             pygame.font.SysFont("DejaVu Sans", 72, bold=True))
    g = Game()
    if record_mode:
        record(screen, fonts, g)
    else:
        play(screen, fonts, g, pygame.time.Clock())
    pygame.quit()


if __name__ == "__main__":
    main()
