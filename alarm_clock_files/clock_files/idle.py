import RPi.GPIO as GPIO
import time
from threading import Thread
import gpio_setup
import config_manager

long_press_time = 2

def monitor_buttons(button_pins, callback):

	"""
	button_pins: dict {name: pin}
	callback(event_type, button_name)
	"""
	def _monitor():
		states={name: {"pressed": False, "start_time": 0, "long_trigger": False} for name in button_pins}
		while True:
			for name, pin in button_pins.items():
				val = GPIO.input(pin)
				info = states[name]
				
				if val == GPIO.LOW:
					if not info["pressed"]:
						info["pressed"] = True
						info["start_time"] = time.time()
						info["long_trigger"] = False
					else:
						if (not info ["long_trigger"]) and (time.time() - info["start_time"] >= long_press_time):
							callback("long",name)
							info["long_trigger"]=True
				else:
					if info ["pressed"]:
						if not info ["long_trigger"]:
							callback("short", name)
						info["pressed"] = False
						info["long_trigger"] = False
			time.sleep(0.01)
	t = Thread(target=_monitor,daemon=True)
	t.start()
	return t

def monitor_rotary_encoder(clk,dt,callback):
	"""calls callback(direction) when rotated"""
	last_clk = GPIO.input(clk)
	
	def _monitor():
		nonlocal last_clk
		while True:
			clk_state = GPIO.input(clk)
			dt_state = GPIO.input(dt)
			if clk_state != last_clk and clk_state==0:
				if dt_state != clk_state:
					callback(1)
				else:
					callback(-1)
			last_clk = clk_state
			time.sleep(0.005)
			
	t = Thread(target= _monitor, daemon= True)
	t.start()
	return t
					
					
					


