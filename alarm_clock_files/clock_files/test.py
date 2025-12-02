import threading
import time
import datetime

import RPi.GPIO as GPIO
import neopixel
import board

import gpio_setup
from config_manager import read_config, write_config
from stepper import forward, backward
import f_update

# ----- Constants -----
LONG_PRESS = 2
STEP_DELAY = 0.003
STEP_PER_REV = 512
MINUTES_PER_REV = 60

NEOPIXEL_PIN = board.D18
NEOPIXEL_PIXELS = 1

step_accumulator = 0.0

last_clk = None
last_tick_time = 0.0
direction_latch = None

led_nood_pwm = None
chromatek = None

alarm_event = threading.Event()
fade_event = threading.Event()
config_lock = threading.Lock()

# ========================= CONFIG ============================
def read_cfg_threadsafe():
    return read_config()

def write_cfg_threadsafe(cfg):
    with config_lock:
        write_config(cfg)

# ========================= LED HELPERS ============================
def set_pm_led_from_hand(cfg):
    pos = cfg.get("hand_position", 0)
    GPIO.output(gpio_setup.led_PM, GPIO.HIGH if pos >= 720 else GPIO.LOW)

def ensure_brightness_pwm(cfg):
    global led_nood_pwm
    if led_nood_pwm is None:
        led_nood_pwm = GPIO.PWM(gpio_setup.led_nood, 1000)
        led_nood_pwm.start(0)
    brightness = max(0, min(100, int(cfg.get("brightness", 50))))
    led_nood_pwm.ChangeDutyCycle(brightness)

def init_chromatek():
    global chromatek
    if chromatek is None:
        chromatek = neopixel.NeoPixel(
            NEOPIXEL_PIN,
            NEOPIXEL_PIXELS,
            auto_write=True,
            pixel_order=neopixel.GRB
        )
        chromatek.brightness = 0.0
        chromatek[0] = (0, 0, 0)

def set_chromatek_color(r, g, b, brightness=None):
    if chromatek is None:
        init_chromatek()
    if brightness is not None:
        chromatek.brightness = max(0.0, min(1.0, brightness))
    chromatek[0] = (int(r), int(g), int(b))

# ========================= ALARM ============================
def start_alarm(cfg, now_min):
    print(f"[DEBUG] start_alarm() now_min={now_min}")
    cfg['alarm_active'] = True
    cfg['alarm_start_min'] = now_min
    cfg['last_ring_min'] = now_min
    cfg.pop('snooze_until', None)
    write_cfg_threadsafe(cfg)
    alarm_event.set()
    print("[DEBUG] alarm_event SET")

def stop_alarm(cfg):
    print("[DEBUG] stop_alarm()")
    cfg['alarm_active'] = False
    cfg.pop('alarm_start_min', None)
    write_cfg_threadsafe(cfg)
    alarm_event.clear()
    print("[DEBUG] alarm_event CLEARED in stop_alarm")

def cancel_alarm_for_day(cfg):
    print("[DEBUG] cancel_alarm_for_day()")
    today = datetime.date.today().isoformat()
    cfg['alarm_disabled_date'] = today
    cfg['alarm_active'] = False
    cfg.pop('alarm_start_min', None)
    cfg.pop('snooze_until', None)
    write_cfg_threadsafe(cfg)
    alarm_event.clear()
    print("[DEBUG] alarm_event CLEARED in cancel_alarm_for_day")

# ========================= REAL-TIME SYNC ============================
def sync_hands_to_real_time(cfg):
    now = datetime.datetime.now()
    now_min = now.hour * 60 + now.minute
    current = cfg.get('hand_position', 0)

    now_min %= 1440
    current %= 1440

    if current == now_min:
        print("[SYNC] Already aligned.")
        return cfg

    forward_m = (now_min - current) % 1440
    backward_m = (current - now_min) % 1440

    if forward_m <= backward_m:
        move_m = forward_m
        direction = "forward"
    else:
        move_m = backward_m
        direction = "backward"

    steps = round((STEP_PER_REV / MINUTES_PER_REV) * move_m)

    print(f"[SYNC] Moving {move_m} minutes → {steps} steps {direction}")

    if direction == "forward":
        forward(STEP_DELAY, steps)
    else:
        backward(STEP_DELAY, steps)

    cfg['hand_position'] = now_min
    write_cfg_threadsafe(cfg)
    set_pm_led_from_hand(cfg)
    return cfg

# ========================= BUZZER THREAD ============================
def buzzer_thread():
    print(f"[DEBUG] buzzer_thread started (piezo={gpio_setup.piezo})")
    while True:
        if alarm_event.is_set():
            print("[DEBUG] buzzer: BEEP")
            end_t = time.time() + 0.2
            GPIO.output(gpio_setup.piezo, GPIO.HIGH)
            while time.time() < end_t:
                if not alarm_event.is_set():
                    print("[DEBUG] buzzer abort early")
                    break
                time.sleep(0.005)
            GPIO.output(gpio_setup.piezo, GPIO.LOW)
            time.sleep(0.2)
        else:
            GPIO.output(gpio_setup.piezo, GPIO.LOW)
            time.sleep(0.05)

# ========================= LED FADE THREAD ============================
def led_fade_thread():
    global led_nood_pwm
    v = 0.1
    direction = 1
    print("[DEBUG] fade thread start")
    while True:
        if fade_event.is_set():
            if led_nood_pwm is None:
                led_nood_pwm = GPIO.PWM(gpio_setup.led_nood, 1000)
                led_nood_pwm.start(0)
            led_nood_pwm.ChangeDutyCycle(v * 100)
            v += direction * 0.04
            if v >= 1.0:
                v = 1.0
                direction = -1
            if v <= 0.05:
                v = 0.05
                direction = 1
            time.sleep(0.03)
        else:
            time.sleep(0.1)

# ========================= EPAPER THREAD ============================
def epaper_auto_thread():
    last_hour = -1
    print("[DEBUG] epaper thread start")
    while True:
        now = datetime.datetime.now()
        if now.hour != last_hour:
            print("[EPAPER] Hour changed -> refresh")
            threading.Thread(target=f_update.update_display_main, daemon=True).start()
            last_hour = now.hour
        time.sleep(60)

# ========================= BUTTON + ENCODER THREAD ============================
def button_polling():
    global last_clk, last_tick_time, direction_latch
    last_clk = GPIO.input(gpio_setup.clk)
    last_tick_time = time.time()
    direction_latch = None

    cfg0 = read_cfg_threadsafe()
    ensure_brightness_pwm(cfg0)
    init_chromatek()
    set_pm_led_from_hand(cfg0)

    print("[DEBUG] button_polling start")
    while True:
        cfg = read_cfg_threadsafe()
        mode = cfg.get('mode', 'idle')

        # ----- ARMING -----
        rg_pressed = GPIO.input(gpio_setup.RGButton) == GPIO.LOW
        if cfg.get("alarm_armed", False) != rg_pressed:
            cfg['alarm_armed'] = bool(rg_pressed)
            write_cfg_threadsafe(cfg)
            print(f"[DEBUG] alarm_armed={cfg['alarm_armed']}")

        # Chromatek brightness
        b = cfg.get("brightness", 50)
        neo_b = max(0.02, b / 100.0)
        if cfg.get("alarm_armed", False):
            set_chromatek_color(255, 255, 0, brightness=neo_b)
        else:
            set_chromatek_color(0, 0, 0, brightness=0.0)

        # ----- RE BUTTON -----
        if GPIO.input(gpio_setup.sw) == GPIO.LOW:
            t0 = time.time()
            while GPIO.input(gpio_setup.sw) == GPIO.LOW:
                time.sleep(0.01)
            d = time.time() - t0

            cfg = read_cfg_threadsafe()
            mode = cfg.get('mode', 'idle')

            # LONG PRESS
            if d >= LONG_PRESS:
                if mode == "idle":
                    print("[DEBUG] RE long → CALIBRATE")
                    cfg['mode'] = 'calibrate'
                    fade_event.set()
                    write_cfg_threadsafe(cfg)
                    threading.Thread(target=f_update.show_calibrate_screen, daemon=True).start()

                elif mode == "calibrate":
                    print("[DEBUG] RE long in CALIBRATE → set hand_position=0, then sync to real time")
                    
                    # 1. Set mechanical zero
                    cfg['hand_position'] = 0
                    write_cfg_threadsafe(cfg)
                    set_pm_led_from_hand(cfg)

                    # 2. Sync to real time
                    cfg = sync_hands_to_real_time(cfg)

                    # 3. Return to idle
                    cfg['mode'] = 'idle'
                    fade_event.clear()
                    write_cfg_threadsafe(cfg)

                elif mode == "set_alarm":
                    print("[DEBUG] RE long → save alarm_time & sync")
                    new_alarm = cfg.get('hand_position', 0)
                    cfg['alarm_time'] = new_alarm
                    write_cfg_threadsafe(cfg)
                    cfg = sync_hands_to_real_time(cfg)
                    cfg['mode'] = 'idle'
                    fade_event.clear()
                    write_cfg_threadsafe(cfg)

            # SHORT PRESS
            else:
                if cfg.get("alarm_active", False):
                    print("[DEBUG] RE short → stop_alarm()")
                    stop_alarm(cfg)
                else:
                    if mode == "idle":
                        print("[DEBUG] RE short idle → refresh epaper")
                        threading.Thread(target=f_update.update_display_main, daemon=True).start()
                    else:
                        print(f"[DEBUG] RE short in mode {mode}")

        # ----- SNOOZE BUTTON -----
        if GPIO.input(gpio_setup.snz) == GPIO.LOW:
            t0 = time.time()
            while GPIO.input(gpio_setup.snz) == GPIO.LOW:
                time.sleep(0.01)
            d = time.time() - t0

            cfg = read_cfg_threadsafe()
            now = datetime.datetime.now()
            now_min = now.hour * 60 + now.minute

            if cfg.get("alarm_active", False):
                if d >= LONG_PRESS:
                    print("[DEBUG] Snooze LONG → cancel_alarm_for_day()")
                    cancel_alarm_for_day(cfg)
                else:
                    snooze_min = (now_min + 5) % 1440
                    cfg['snooze_until'] = snooze_min
                    write_cfg_threadsafe(cfg)
                    stop_alarm(cfg)
                    print(f"[DEBUG] Snooze SHORT → snooze_until={snooze_min}")
                continue

            if mode == "idle" and d >= LONG_PRESS:
                print("[DEBUG] Snooze long in idle → SET_ALARM")
                cfg['mode'] = 'set_alarm'
                write_cfg_threadsafe(cfg)
                fade_event.set()
                threading.Thread(target=f_update.show_set_alarm_screen, daemon=True).start()

        # ----- ENCODER -----
        clk = GPIO.input(gpio_setup.clk)
        if clk != last_clk:
            now_t = time.time()
            if now_t - last_tick_time < 0.002:
                last_clk = clk
                continue

            if clk == GPIO.LOW:
                time.sleep(0.001)
                d1 = GPIO.input(gpio_setup.dt)
                time.sleep(0.0005)
                d2 = GPIO.input(gpio_setup.dt)
                if d1 == d2:
                    direction_latch = "CW" if d1 else "CCW"
                else:
                    direction_latch = None

            elif clk == GPIO.HIGH and direction_latch is not None:
                cfg = read_cfg_threadsafe()
                mode = cfg.get('mode', 'idle')
                direction = direction_latch
                direction_latch = None

                if mode in ("calibrate", "set_alarm"):
                    steps5 = round((STEP_PER_REV / MINUTES_PER_REV) * 5)
                    if direction == "CW":
                        forward(STEP_DELAY, steps5)
                        cfg['hand_position'] = (cfg.get('hand_position', 0) + 5) % 1440
                    else:
                        backward(STEP_DELAY, steps5)
                        cfg['hand_position'] = (cfg.get('hand_position', 0) - 5) % 1440
                    write_cfg_threadsafe(cfg)
                    set_pm_led_from_hand(cfg)
                    print(f"[DEBUG] {mode}: encoder {direction} → +/-5 min")

                else:
                    b = cfg.get('brightness', 50)
                    if direction == "CW":
                        b = min(100, b + 5)
                    else:
                        b = max(0, b - 5)
                    cfg['brightness'] = b
                    write_cfg_threadsafe(cfg)
                    if not fade_event.is_set():
                        ensure_brightness_pwm(cfg)
                    if cfg.get("alarm_armed", False):
                        set_chromatek_color(255, 255, 0, brightness=max(0.02, b/100.0))
                    else:
                        set_chromatek_color(0, 0, 0, brightness=0.0)
                    print(f"[DEBUG] Idle enc {direction} → brightness {b}%")

            last_clk = clk
            last_tick_time = now_t

        time.sleep(0.002)

# ========================= CLOCK THREAD ============================
def clock_thread():
    global step_accumulator
    print("[DEBUG] clock_thread start")
    while True:
        now = datetime.datetime.now()
        now_min = now.hour * 60 + now.minute
        today = now.date().isoformat()

        cfg = read_cfg_threadsafe()
        mode = cfg.get('mode', 'idle')

        rg_pressed = (GPIO.input(gpio_setup.RGButton) == GPIO.LOW)
        if cfg.get("alarm_armed", False) != rg_pressed:
            cfg['alarm_armed'] = rg_pressed
            write_cfg_threadsafe(cfg)

        if mode == "set_alarm":
            time.sleep(1)
            continue

        # auto-move clock
        if mode == "idle":
            pos = cfg.get("hand_position", 0)
            if pos != now_min:
                mins = (now_min - pos) % 1440
                step_accumulator += (STEP_PER_REV / MINUTES_PER_REV) * mins
                steps = int(step_accumulator)
                step_accumulator -= steps
                if steps:
                    forward(STEP_DELAY, steps)
                cfg['hand_position'] = now_min
                write_cfg_threadsafe(cfg)
                set_pm_led_from_hand(cfg)
                if not fade_event.is_set():
                    ensure_brightness_pwm(cfg)

        # alarm trigger logic
        cfg = read_cfg_threadsafe()
        armed = cfg.get("alarm_armed", False)
        alarm_time = cfg.get("alarm_time", None)
        snooze_until = cfg.get("snooze_until", None)
        disabled_date = cfg.get("alarm_disabled_date", None)
        active = cfg.get("alarm_active", False)
        last_ring = cfg.get("last_ring_min", None)

        should_ring = False
        if armed and not active and disabled_date != today:
            if last_ring != now_min:
                if alarm_time == now_min:
                    should_ring = True
                elif snooze_until == now_min:
                    should_ring = True

        if should_ring:
            print(f"[DEBUG] Alarm SHOULD ring! now_min={now_min}")
            start_alarm(cfg, now_min)

        # auto-cancel alarm after 10 min
        cfg = read_cfg_threadsafe()
        if cfg.get("alarm_active", False):
            start_m = cfg.get("alarm_start_min", None)
            if start_m is not None:
                elapsed = (now_min - start_m) % 1440
                if elapsed >= 10:
                    print("[DEBUG] Auto-cancel (10 min)")
                    cancel_alarm_for_day(cfg)

        time.sleep(1)

# ========================= MAIN ============================
if __name__ == "__main__":
    gpio_setup.setup_pins()
    GPIO.output(gpio_setup.led_PM, GPIO.LOW)

    cfg0 = read_cfg_threadsafe()
    ensure_brightness_pwm(cfg0)
    set_pm_led_from_hand(cfg0)
    init_chromatek()

    print("[DEBUG] Starting threads...")

    threading.Thread(target=buzzer_thread, daemon=True).start()
    threading.Thread(target=button_polling, daemon=True).start()
    threading.Thread(target=clock_thread, daemon=True).start()
    threading.Thread(target=led_fade_thread, daemon=True).start()
    threading.Thread(target=epaper_auto_thread, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[DEBUG] KeyboardInterrupt, cleaning up")
        if led_nood_pwm:
            led_nood_pwm.stop()
        GPIO.output(gpio_setup.piezo, GPIO.LOW)
        GPIO.cleanup()
