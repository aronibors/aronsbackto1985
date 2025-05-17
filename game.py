#!/usr/bin/env python3
import curses
import time
import random
import numpy as np
import simpleaudio as sa

# Configuration
TICK = 0.05                       # Frame delay
INITIAL_SPAWN_RATE = 0.2          # Initial obstacle spawn chance
MAX_SPAWN_RATE = 1.0              # Max spawn chance
SPAWN_INCREASE = 0.05             # Spawn increase per speed-up
GRAVITY = 1                       # Gravity per frame
JUMP_VELOCITY = -5                # Jump velocity
SPEED_UP_INTERVAL = 10.0          # Seconds between speed-ups
LEVEL_COUNT = 3                   # Levels to complete

# Audio helpers
def play_tone(freq, duration_ms, block=True):
    fs = 44100
    t = np.linspace(0, duration_ms/1000, int(fs*duration_ms/1000), False)
    wave = np.sin(freq*2*np.pi*t)*0.3
    audio = (wave*32767).astype(np.int16)
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    if block:
        play_obj.wait_done()

def play_square_tone(freq, duration_ms, block=True):
    fs = 44100
    t = np.linspace(0, duration_ms/1000, int(fs*duration_ms/1000), False)
    wave = np.sign(np.sin(freq*2*np.pi*t))*0.3
    audio = (wave*32767).astype(np.int16)
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    if block:
        play_obj.wait_done()

# Level complete: square 'weep' tones
def play_success_sound():
    freqs = [500, 750, 1125]
    for f in freqs:
        play_square_tone(f, 100)
        time.sleep(0.05)

# Game-over: 'wah wah waaaah' sine tones
def play_fail_sound():
    base = 450
    freqs = [base, int(base*0.67), int(base*0.67*0.67)]
    durations = [660, 660, 1000]
    for f, d in zip(freqs, durations):
        play_tone(f, d)
        time.sleep(0.1)

# Single level
def play_level(stdscr, level, carry):
    sh, sw = stdscr.getmaxyx()
    x = sw//4
    y = sh-2
    vy = 0
    on_ground = True
    obstacles = []
    speed = level
    spawn_rate = min(MAX_SPAWN_RATE, INITIAL_SPAWN_RATE + 0.1*(level-1))
    lives = 1 + carry
    speed_ups = 0
    last_up = time.time()
    ship_char = '^'

    while True:
        t0 = time.time()
        # Speed-ups
        if t0 - last_up >= SPEED_UP_INTERVAL:
            speed += 1
            spawn_rate = min(MAX_SPAWN_RATE, spawn_rate + SPAWN_INCREASE)
            speed_ups += 1
            last_up = t0
            if speed_ups >= 3:
                play_success_sound()
                stdscr.clear()
                msg = f'Level {level} Complete!'
                stdscr.addstr(sh//2, (sw-len(msg))//2, msg, curses.color_pair(3))
                stdscr.refresh()
                time.sleep(3)
                return True, lives

        # Input
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            return False, lives
        elif key == curses.KEY_LEFT and x > 1:
            x -= 1
        elif key == curses.KEY_RIGHT and x < sw-2:
            x += 1
        elif key == ord(' ') and on_ground:
            play_square_tone(700, 50, block=False)
            vy = JUMP_VELOCITY
            on_ground = False

        # Gravity
        if not on_ground:
            y += vy
            vy += GRAVITY
            if y >= sh-2:
                y = sh-2
                vy = 0
                on_ground = True

        # Spawn obstacles
        if random.random() < spawn_rate:
            obstacles.append({'row': random.randint(1, sh-2), 'col': sw-2})
        # Move & remove
        for o in obstacles:
            o['col'] -= speed
        obstacles = [o for o in obstacles if o['col'] > 0]

        # Collision
        for o in obstacles.copy():
            if o['col'] == x and o['row'] == y:
                play_square_tone(300, 50, block=False)
                if lives > 0:
                    lives -= 1
                    obstacles.remove(o)
                else:
                    play_fail_sound()
                    stdscr.clear()
                    msg = 'GAME OVER'
                    stdscr.addstr(sh//2, (sw-len(msg))//2, msg, curses.color_pair(3))
                    stdscr.refresh()
                    time.sleep(3)
                    return False, 0

        # Draw
        stdscr.clear()
        stdscr.border()
        stdscr.addch(y, x, ship_char, curses.color_pair(1))
        for o in obstacles:
            stdscr.addch(o['row'], o['col'], '-', curses.color_pair(2))
        stdscr.addstr(0,2, f'Lvl:{level}/{LEVEL_COUNT}', curses.color_pair(3))
        stdscr.addstr(0,15, f'Spd:{speed}', curses.color_pair(3))
        stdscr.addstr(0,25, f'Spawn:{spawn_rate:.2f}', curses.color_pair(3))
        stdscr.addstr(0,40, f'Life:{lives}', curses.color_pair(3))
        stdscr.refresh()

        # Throttle
        dt = time.time() - t0
        if dt < TICK:
            time.sleep(TICK - dt)

# Main
def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
    carry_lives = 0
    for lvl in range(1, LEVEL_COUNT+1):
        proceed, carry_lives = play_level(stdscr, lvl, carry_lives)
        if not proceed:
            return
    play_success_sound()
    stdscr.clear()
    msg = 'CONGRATULATIONS! YOU WON!'
    sh, sw = stdscr.getmaxyx()
    stdscr.addstr(sh//2, (sw-len(msg))//2, msg, curses.color_pair(3))
    stdscr.refresh()
    time.sleep(3)

if __name__ == '__main__':
    curses.wrapper(main)
