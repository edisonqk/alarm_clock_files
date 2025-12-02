import sys
import os
import logging
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, date
import time
import requests
import threading
import json

lock = threading.Lock()

def get_hand_position_str(json_file="config.json"):
    with open(json_file, "r") as f:
        data = json.load(f)
    return data.get("hand_position", "Not Found")

def get_alarm_str(json_file="config.json"):
    with open(json_file, "r") as f:
        data = json.load(f)
    return data.get("alarm_time", "Not Found")

def readable_time(mtime):
    mtime = int(mtime)
    hours = mtime // 60
    mins = mtime % 60
    time_str = f"{hours:02d}:{mins:02d}"
    return time_str


def show_calibrate_screen():
    """
    Minimal text screen with instructions for CALIBRATE mode.
    """
    with lock:
        try:
            epd = epd2in13_V4.EPD()
            epd.init()
            epd.Clear(0xFF)

            w = epd.height
            h = epd.width
            font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
            font14 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)

            base_image = Image.new('1', (w, h), 255)
            draw = ImageDraw.Draw(base_image)

            draw.text((10, 5), "CALIBRATE MODE", font=font24, fill=0)
            draw.line([(0, 35), (w, 35)], fill=0, width=1)

            draw.text((10, 45), "- Turn encoder to move hands", font=font14, fill=0)
            draw.text((10, 65), "- Hold RE button to exit", font=font14, fill=0)

            epd.display(epd.getbuffer(base_image))

        except IOError as e:
            logging.info(e)
        except KeyboardInterrupt:
            logging.info("ctrl + c:")
            epd2in13_V4.epdconfig.module_exit(cleanup=True)
            exit()
        finally:
            print("epaper: show_calibrate_screen done")


def show_set_alarm_screen():
    """
    Minimal text screen with instructions for SET ALARM mode.
    """
    with lock:
        try:
            epd = epd2in13_V4.EPD()
            epd.init()
            epd.Clear(0xFF)

            w = epd.height
            h = epd.width
            font24 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
            font14 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)

            base_image = Image.new('1', (w, h), 255)
            draw = ImageDraw.Draw(base_image)

            draw.text((10, 5), "SET ALARM MODE", font=font24, fill=0)
            draw.line([(0, 35), (w, 35)], fill=0, width=1)

            draw.text((10, 40), "- Turn encoder to set time", font=font14, fill=0)
            draw.text((10, 80), "- Hold RE to save & exit", font=font14, fill=0)
            draw.text((10, 60), "- Press RE to see exact time", font=font14, fill=0)

            # show current hand position as time
            hand_position = get_hand_position_str()
            try:
                hand_position = int(hand_position)
                time_str = readable_time(hand_position)
                draw.text((10, 100), f"Alarm Time: {time_str}", font=font14, fill=0)
            except Exception:
                pass

            epd.display(epd.getbuffer(base_image))

        except IOError as e:
            logging.info(e)
        except KeyboardInterrupt:
            logging.info("ctrl + c:")
            epd2in13_V4.epdconfig.module_exit(cleanup=True)
            exit()
        finally:
            print("epaper: show_set_alarm_screen done")


def update_display_main():
    api_key = '4109aa83986446fd92ff35d9eeacd9c3'  # your API key
    city = 'Miami' # your city name
    units = 'imperial' # your preferred units
    base_url = 'https://api.openweathermap.org/data/3.0/onecall?'
    url = (base_url + 'appid=' + api_key +
           '&lat=25.77&lon=-80.19&units=' + units +
           '&exclude=minutely,hourly') #find the lattitude and longitude of your location online
    response = requests.get(url).json()

    forecast = []
    with lock:
        try:
            epd = epd2in13_V4.EPD()
            epd.init()
            epd.Clear(0xFF)

            w = epd.height
            h = epd.width
            font20 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
            font12 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
            font15 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 14)
            font10 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 10)

            current_time = time.strftime('%H:%M')
            today = date.today()
            current_date = today.strftime("%A, %b %d")

            for day in response['daily']:
                forecastx = {
                    'date': datetime.utcfromtimestamp(day['dt']).strftime('%A. %b %d'),
                    'min_date': datetime.utcfromtimestamp(day['dt']).strftime('%a'),
                    'main': day['weather'][0]['main'],
                    'id': day['weather'][0]['id'],
                    'description': day['weather'][0]['description'],
                    'avg_temp': round((day['temp']['min'] + day['temp']['max']) / 2),
                    'max_temp': round(day['temp']['max']),
                    'min_temp': round(day['temp']['min']),
                    'precipitation': int(day['pop'] * 100)
                }
                forecast.append(forecastx)

            base_image = Image.new('1', (w, h), 255)
            basedraw = ImageDraw.Draw(base_image)

            basedraw.line([(0, 25), (250, 25)], fill=0, width=1)
            basedraw.text((2, 0), current_date, font=font20, fill=0)
            basedraw.rectangle([(0, 28), (39, 42)], fill=0, outline=0, width=1)
            basedraw.text((2, 27), city, font=font12, fill=255)
            basedraw.text((43, 27), str(forecast[0]['description']), font=font12, fill=0)
            basedraw.rectangle([(52, 45), (81, 58)], fill=0, outline=0, width=1)
            basedraw.text((53, 43), f"{forecast[0]['max_temp']} F", font=font15, fill=255)
            basedraw.text((52, 59), f"{forecast[0]['min_temp']} F", font=font15, fill=0)
            basedraw.text((64, 76), f"{forecast[0]['precipitation']}%", font=font15, fill=0)
            basedraw.rectangle([(190, 0), (250, 25)], fill=0, outline=0, width=1)
            basedraw.text((192, 24), 'last updated', font=font10, fill=0)
            basedraw.text((195, 2), current_time, font=font20, fill=255)

            icon_map = {
                (200, 232): '/home/edison/weather_icons/thunderstorm.bmp',
                (300, 531): '/home/edison/weather_icons/raining2.bmp',
                (600, 622): '/home/edison/weather_icons/snowing.bmp',
                (701, 781): '/home/edison/weather_icons/atmosphere.bmp',
                (800, 800): '/home/edison/weather_icons/clear.bmp',
                (801, 802): '/home/edison/weather_icons/cloud.bmp',
                (803, 804): '/home/edison/weather_icons/very_cloudy.bmp'
            }

            def get_icon_path(weather_id):
                for id_range, icon_path in icon_map.items():
                    if id_range[0] <= weather_id <= id_range[1]:
                        return icon_path

            icons = []
            icons_small = []
            for day in response['daily'][:4]:
                weather_id = day['weather'][0]['id']
                path = get_icon_path(weather_id)
                icon_image = Image.open(path).convert('1')
                icon_image_small = icon_image.resize((23, 23))
                icons.append(icon_image)
                icons_small.append(icon_image_small)

            base_image.paste(icons[0], (0, 45))

            droplet = Image.open('/home/edison/droplet.bmp').convert('1')
            droplet_small = droplet.resize((13, 13))
            base_image.paste(droplet_small, (50, 78))

            basedraw.rectangle([(0, 45), (50, 95)], fill=None, outline=0, width=1)

            basedraw.text(
                (0, 103),
                f"{forecast[1]['min_date']}|{forecast[1]['avg_temp']} F",
                font=font15, fill=0
            )
            base_image.paste(icons_small[1], (58, 99))

            basedraw.text(
                (85, 103),
                f"{forecast[2]['min_date']}|{forecast[2]['avg_temp']} F",
                font=font15, fill=0
            )
            base_image.paste(icons_small[2], (143, 99))

            basedraw.text(
                (168, 103),
                f"{forecast[3]['min_date']}|{forecast[3]['avg_temp']} F",
                font=font15, fill=0
            )
            base_image.paste(icons_small[3], (230, 99))

            basedraw.line([(0, 98), (250, 98)], fill=0, width=1)
            basedraw.line([(83, 98), (83, 122)], fill=0, width=1)
            basedraw.line([(166, 98), (166, 122)], fill=0, width=1)

            alarm_str = get_alarm_str()
            try:
                alarm_min = int(alarm_str)
                alarm_str_fmt = readable_time(alarm_min)
            except Exception:
                alarm_str_fmt = str(alarm_str)
            basedraw.text((120, 55), f"Alarm Time: {alarm_str_fmt}", font=font15, fill=0)

            epd.display(epd.getbuffer(base_image))

        except IOError as e:
            logging.info(e)
        except KeyboardInterrupt:
            logging.info("ctrl + c:")
            epd2in13_V4.epdconfig.module_exit(cleanup=True)
            exit()
        finally:
            print("epaper: update_display_main done")
