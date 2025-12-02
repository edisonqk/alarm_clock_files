import RPi.GPIO as GPIO

# ULN2003AN stepper driver (BCM pins)
IN1 = 5
IN2 = 6
IN3 = 12
IN4 = 13
stepper_pins = [IN1, IN2, IN3, IN4]

# Rotary encoder (BCM)
clk = 21      # Board 40
dt = 20       # Board 38
sw = 16       # Board 36 (encoder push button)

# Snooze button
snz = 4       # Board 7

# LEDs
led_nood = 19  # Board 35
led_PM = 2     # Board 3

# Piezo (active buzzer)
piezo = 3      # Board 5

# Chromatek RGB button (mechanical switch input)
RGButton = 26  # Board 37

def setup_pins():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Inputs
    GPIO.setup(clk, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(dt, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(sw, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(snz, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(RGButton, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Outputs: stepper pins
    GPIO.setup(IN1, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(IN2, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(IN3, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(IN4, GPIO.OUT, initial=GPIO.LOW)

    # LEDs and piezo
    GPIO.setup(led_nood, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(led_PM, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(piezo, GPIO.OUT, initial=GPIO.LOW)
