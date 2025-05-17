#!/usr/bin/env python3
import curses, time, random, math, threading
import numpy as np, simpleaudio as sa

# ― Config ―
FS = 44100           # Sample rate
BG_SEC = 30          # Background track length (s)
INT_INC = 0.1        # +10% pitch/tempo per level
GR = 1               # Gravity per frame
LEVELS = 3
SPAWN0 = 0.2
SPEED_INT = 10       # Seconds between speedups
TICK = 0.05          # Frame delay

# ― Tone generation ―
def gen_sq(freq, ms):
    t = np.linspace(0, ms/1000, int(FS*ms/1000), False)
    w = np.sign(np.sin(2*math.pi*freq*t)) * 0.3
    return (w*32767).astype(np.int16)

JUMP = gen_sq(700,50)
HIT  = gen_sq(300,50)
WIN  = [gen_sq(f,100) for f in (500,750,1125)]
FAIL = [gen_sq(f,d) for f,d in ((450,660),(300,660),(200,1000))]

# ― Build a non-repeating 30s track ―
def build_bg(level):
    notes = [440,494,523,587,659,698,784]
    factor = 1 + INT_INC*(level-1)
    target = int(FS*BG_SEC)
    buf = np.zeros(0, np.int16)
    while buf.size < target:
        f = random.choice(notes)
        d = random.choice((100,150,200,300))
        buf = np.concatenate([buf, gen_sq(int(f*factor), d)])
    return buf[:target]

# ― Playback helpers ―
def play_async(buf):
    sa.play_buffer(buf, 1, 2, FS)

def play_block(buf):
    sa.play_buffer(buf, 1, 2, FS).wait_done()

# ― Level loop ―
def play_level(stdscr, lvl, carry):
    sh, sw = stdscr.getmaxyx()
    # jump velocities
    v1 = -int(math.sqrt(2*GR*(0.18*sh)))
    v2 = -int(math.sqrt(2*GR*(0.36*sh)))

    # start bg music
    bg = build_bg(lvl)
    threading.Thread(target=play_async, args=(bg,), daemon=True).start()

    x, y, vy = sw//4, sh-2, 0
    on_ground, jumps = True, 0
    obs = []
    speed = lvl
    spawn = min(1.0, SPAWN0 + 0.1*(lvl-1))
    lives = 1 + carry
    ups, last_up = 0, time.time()

    while True:
        now = time.time()
        # speed-up events
        if now - last_up >= SPEED_INT:
            speed += 1
            spawn = min(1.0, spawn + 0.05)
            ups += 1
            last_up = now
            if ups >= 3:
                for w in WIN: play_block(w)
                stdscr.clear()
                msg = f"Level {lvl} Complete!"
                stdscr.addstr(sh//2, (sw-len(msg))//2, msg, curses.color_pair(3))
                stdscr.refresh()
                time.sleep(2)
                return True, lives

        # input
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            return False, lives
        if key == curses.KEY_LEFT and x > 1:
            x -= 1
        if key == curses.KEY_RIGHT and x < sw-2:
            x += 1
        if key == ord(' '):
            if on_ground:
                play_block(JUMP)
                vy, on_ground, jumps = v1, False, 1
            elif jumps == 1:
                play_block(JUMP)
                vy, jumps = v2, 2

        # physics
        if not on_ground:
            y += vy
            vy += GR
            if y >= sh-2:
                y, vy, on_ground, jumps = sh-2, 0, True, 0
            if y < 1:
                y, vy = 1, 0

        # spawn & move obstacles
        if random.random() < spawn:
            obs.append({'r': random.randint(1, sh-2), 'c': sw-2})
        for o in obs:
            o['c'] -= speed
        obs = [o for o in obs if o['c'] > 0]

        # collisions
        for o in obs.copy():
            if o['c'] == x and o['r'] == y:
                play_block(HIT)
                if lives > 0:
                    lives -= 1
                    obs.remove(o)
                else:
                    for f in FAIL: play_block(f)
                    stdscr.clear()
                    stdscr.addstr(sh//2, (sw-9)//2, "GAME OVER",
                                  curses.color_pair(3))
                    stdscr.refresh()
                    time.sleep(2)
                    return False, 0

        # draw
        stdscr.clear()
        stdscr.border()
        stdscr.addch(y, x, '^', curses.color_pair(1))
        for o in obs:
            stdscr.addch(o['r'], o['c'], '-', curses.color_pair(2))
        stdscr.addstr(0, 2,  f'Lvl:{lvl}/{LEVELS}', curses.color_pair(3))
        stdscr.addstr(0, 15, f'Spd:{speed}',      curses.color_pair(3))
        stdscr.addstr(0, 30, f'Spawn:{spawn:.2f}',curses.color_pair(3))
        stdscr.addstr(0, 45, f'Life:{lives}',     curses.color_pair(3))
        stdscr.refresh()

        # throttle
        dt = time.time() - now
        if dt < TICK:
            time.sleep(TICK - dt)

# ― Main ―
def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLUE,  0)
    curses.init_pair(2, curses.COLOR_RED,   0)
    curses.init_pair(3, curses.COLOR_WHITE, 0)

    carry = 0
    for lvl in range(1, LEVELS+1):
        ok, carry = play_level(stdscr, lvl, carry)
        if not ok:
            return

    # after level 3
    stdscr.clear()
    msg = "Congratulations! You Won!"
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h//2, (w-len(msg))//2, msg, curses.color_pair(3))
    stdscr.refresh()
    time.sleep(3)

if __name__ == '__main__':
    curses.wrapper(main)
