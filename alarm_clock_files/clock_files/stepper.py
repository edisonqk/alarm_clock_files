#!/usr/bin/env python
import RPi.GPIO as GPIO
import time
from gpio_setup import IN1, IN2, IN3, IN4

def setStep(w1, w2, w3, w4):
    GPIO.output(IN1, w1)
    GPIO.output(IN2, w2)
    GPIO.output(IN3, w3)
    GPIO.output(IN4, w4)

def forward(delay, steps):
    """
    Move the stepper motor.
    steps > 0 : clockwise
    steps < 0 : counter-clockwise
    """
    direction = 1 if steps >= 0 else -1
    steps = abs(int(steps))

    for _ in range(steps):
        if direction == 1:
            # CW sequence
            setStep(1, 0, 0, 0)
            time.sleep(delay)
            setStep(0, 1, 0, 0)
            time.sleep(delay)
            setStep(0, 0, 1, 0)
            time.sleep(delay)
            setStep(0, 0, 0, 1)
            time.sleep(delay)
        else:
            # CCW sequence
            setStep(0, 0, 0, 1)
            time.sleep(delay)
            setStep(0, 0, 1, 0)
            time.sleep(delay)
            setStep(0, 1, 0, 0)
            time.sleep(delay)
            setStep(1, 0, 0, 0)
            time.sleep(delay)

def backward(delay, steps):
    """
    Convenience wrapper: positive steps -> backward.
    """
    forward(delay, -abs(int(steps)))
