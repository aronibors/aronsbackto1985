#!/usr/bin/env python3
import curses
import time
import random
import numpy as np
import simpleaudio as sa

# Configuration
TICK = 0.05                       # Frame delay (seconds)
INITIAL_SPAWN_RATE = 0.2          # Initial obstacle spawn chance per frame
MAX_SPAWN_RATE = 1.0              # Cap for spawn rate
SPAWN_INCREASE = 0.05             # Spawn rate increase per speed-up
GRAVITY = 1                       # Gravity per frame
JUMP_VELOCITY = -5                # Initial jump velocity
SPEED_UP_INTERVAL = 10.0          # Seconds between speed increases (speed-up events)
LEVEL_COUNT = 3                   # Number of levels to complete

# Audio helper
def play_tone(freq, duration_ms, block=True):
    """
    Generate and play a sine wave at freq Hz for duration_ms ms.
    If block is True, wait until done; otherwise play asynchronously.
    """
    fs = 44100  # sampling rate
    t = np.linspace(0, duration_ms / 1000, int(fs * duration_ms / 1000), False)
    wave = np.sin(freq * 2 * np.pi * t) * 0.3
    audio = (wave * 32767).astype(np.int16)
    play_obj = sa.play_buffer(audio, 1, 2, fs)
    if block:
        play_obj.wait_done()

# Level completion: three 'weep' tones starting at 500Hz, +50% each, 200ms each
def play_success_sound():
    freqs = [500, int(500 * 1.5), int(500 * 1.5 * 1.5)]
    for f in freqs:
        play_tone(f, 200, block=True)
        time.sleep(0.1)

# Game over: three 'wah' tones starting at 450Hz, -33% each; durations 660ms,660ms,1000ms
def play_fail_sound():
    base = 450
    freqs = [
        base,
        int(base * (1 - 0.33)),
        int(base * (1 - 0.33) * (1 - 0.33))
    ]
    durations = [660, 660, 1000]
    for f, d in zip(freqs, durations):
        play_tone(f, d, block=True)
        time.sleep(0.1)

# Main game loop per level
def play_level(stdscr, level_num, carry_lives):
    sh, sw = stdscr.getmaxyx()
    char_x = sw // 4
    char_y = sh - 2
    vy = 0
    on_ground = True
    lines = []
    speed = level_num
    spawn_rate = min(MAX_SPAWN_RATE, INITIAL_SPAWN_RATE + (level_num - 1) * 0.1)
    hits_remaining = 1 + carry_lives
    speed_ups = 0
    last_speed_time = time.time()

    while True:
        start = time.time()
        now = start
        # Speed-ups
        if now - last_speed_time > SPEED_UP_INTERVAL:
            speed += 1
            spawn_rate = min(MAX_SPAWN_RATE, spawn_rate + SPAWN_INCREASE)
            speed_ups += 1
            last_speed_time = now
            if speed_ups >= 3:
                play_success_sound()
                stdscr.clear()
                msg = f'Level {level_num} Complete!'
                stdscr.addstr(sh // 2, (sw - len(msg)) // 2, msg)
                stdscr.refresh()
                time.sleep(3)
                return True, hits_remaining

        # Input
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            return False, hits_remaining
        elif key == curses.KEY_LEFT and char_x > 1:
            char_x -= 1
        elif key == curses.KEY_RIGHT and char_x < sw - 2:
            char_x += 1
        elif key == ord(' ') and on_ground:
            # Jump sound non-blocking
            play_tone(700, 100, block=False)
            vy = JUMP_VELOCITY
            on_ground = False

        # Gravity
        if not on_ground:
            char_y += vy
            vy += GRAVITY
            if char_y >= sh - 2:
                char_y = sh - 2
                vy = 0
                on_ground = True

        # Spawn obstacles
        if random.random() < spawn_rate:
            row = random.randint(1, sh - 3)
            lines.append({'row': row, 'col': sw - 2})
        # Move obstacles
        for ln in lines:
            ln['col'] -= speed
        lines = [ln for ln in lines if ln['col'] > 0]

        # Collision
        for ln in list(lines):
            if ln['col'] == char_x and ln['row'] == char_y:
                # Hit sound non-blocking
                play_tone(300, 100, block=False)
                if hits_remaining > 0:
                    hits_remaining -= 1
                    lines.remove(ln)
                else:
                    play_fail_sound()
                    stdscr.clear()
                    msg = 'GAME OVER'
                    stdscr.addstr(sh // 2, (sw - len(msg)) // 2, msg)
                    stdscr.refresh()
                    time.sleep(3)
                    return False, 0

        # Draw
        stdscr.clear()
        stdscr.border()
        stdscr.addch(int(char_y), int(char_x), '@')
        for ln in lines:
            stdscr.addch(ln['row'], ln['col'], '-')
        stdscr.addstr(0, 2, f'Lvl:{level_num}/{LEVEL_COUNT}')
        stdscr.addstr(0, 12, f'Spd:{speed}')
        stdscr.addstr(0, 22, f'Spawn:{spawn_rate:.2f}')
        stdscr.addstr(0, 36, f'Life:{hits_remaining}')

        stdscr.refresh()
        # Frame throttle
        elapsed = time.time() - start
        if elapsed < TICK:
            time.sleep(TICK - elapsed)

# Overall game
def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    carry_lives = 0
    for lvl in range(1, LEVEL_COUNT + 1):
        proceed, carry_lives = play_level(stdscr, lvl, carry_lives)
        if not proceed:
            return
    play_success_sound()
    stdscr.clear()
    msg = 'CONGRATULATIONS! YOU WON!'
    sh, sw = stdscr.getmaxyx()
    stdscr.addstr(sh // 2, (sw - len(msg)) // 2, msg)
    stdscr.refresh()
    time.sleep(3)

if __name__ == '__main__':
    curses.wrapper(main)

