#!/usr/bin/python3

import argparse
import datetime
import time
import aqi
from sds011 import SDS011

def parse_args():
    parser = argparse.ArgumentParser(description="Measure air quality using an SDS011 sensor.")

    parser.add_argument("--delay", "-d", default=1200, metavar="SECONDS", type=int, help="seconds to pause after getting data with the sensor before taking another measure (default: 1200, ie. 20 minutes)")
    parser.add_argument("--log", "-l", metavar="FILE", help="path to the CSV file where data will be appended")
    parser.add_argument("--measures", "-m", default=3, metavar="N", type=int, help="get PM2.5 and PM10 values by taking N consecutive measures (default: 3)")
    parser.add_argument("--omnia-leds", "-o", action="store_true", help="set Turris Omnia LED colors according to measures (User #1 LED for PM2.5 and User #2 LED for PM10)")
    parser.add_argument("--sensor", "-s", default="/dev/ttyUSB0", metavar="FILE", help="path to the SDS011 sensor (default: '/dev/ttyUSB0')")
    parser.add_argument("--sensor-operation-delay", "-p", default=10, metavar="SECONDS", type=int, help="seconds to let the sensor start (default: 10)")
    parser.add_argument("--sensor-start-delay", "-t", default=1, metavar="SECONDS", type=int, help="seconds to let the sensor perform an operation : taking a measure or going to sleep (default: 1)")

    return parser.parse_args()

def get_data(sensor, measures, start_delay, operation_delay):
    # Wake-up sensor
    sensor.sleep(sleep=False)

    pmt_2_5 = 0.0
    pmt_10 = 0.0

    # Let the sensor at least 10 seconds to start in order to get precise values
    time.sleep(start_delay)

    # Take several measures
    for _ in range(measures):
        x = sensor.query()
        pmt_2_5 = pmt_2_5 + x[0]
        pmt_10 = pmt_10 + x[1]
        time.sleep(operation_delay)

    # Round the measures as a number with one decimal
    pmt_2_5 = round(pmt_2_5/measures, 1)
    pmt_10 = round(pmt_10/measures, 1)

    # Put the sensor to sleep
    sensor.sleep(sleep=True)
    time.sleep(operation_delay)

    return pmt_2_5, pmt_10

def conv_aqi(pmt_2_5, pmt_10):
    # Compute the AQI index for PM2.5
    aqi_2_5 = aqi.to_iaqi(aqi.POLLUTANT_PM25, str(pmt_2_5))
    # Compute the AQI index for PM10
    aqi_10 = aqi.to_iaqi(aqi.POLLUTANT_PM10, str(pmt_10))

    return aqi_2_5, aqi_10

def get_aqi_color(aqi):
    if (aqi > 0) and (aqi <= 50):
        # Green : 0 < aqi <= 50
        return "0 255 0"
    elif aqi <= 100:
        # Yellow : 51 < aqi <= 100
        return "255 255 0"
    elif aqi <= 150:
        # Orange : 100 < aqi <= 150
        return "255 153 0"
    elif aqi <= 200:
        # Red : 150 < aqi <= 200
        return "255 0 0"
    elif aqi <= 300:
        # Indigo : 200 < aqi <= 300
        return "84 0 153"
    elif aqi > 300:
        # Maroon : 300 < aqi
        return "128 0 0"

def set_turris_omnia_led(user1_color, user2_color):
    # LED User #1 ("A")
    with open("/sys/class/leds/omnia-led:user1/autonomous", "w") as led_user1_autonomous:
        led_user1_autonomous.write("0\n")
    # LED User #2 ("B")
    with open("/sys/class/leds/omnia-led:user2/autonomous", "w") as led_user2_autonomous:
        led_user2_autonomous.write("0\n")

    # LED User #1 ("A")
    with open("/sys/class/leds/omnia-led:user1/color", "w") as led_user1_color:
        led_user1_color.write(user1_color + "\n")
    # LED User #2 ("B")
    with open("/sys/class/leds/omnia-led:user2/color", "w") as led_user2_color:
        led_user2_color.write(user2_color + "\n")

def save_log(logfile, pmt_2_5, aqi_2_5, pmt_10, aqi_10):
    try:
        with open(logfile, "a") as log:
            dt = datetime.datetime.now()
            log.write("{},{},{},{},{}\n".format(dt, pmt_2_5, aqi_2_5, pmt_10, aqi_10))
            log.close()
    except:
        print("[INFO] Failure in logging data") 


args = parse_args()
sensor = SDS011(args.sensor)

while(True):
    pmt_2_5, pmt_10 = get_data(sensor, args.measures, args.sensor_start_delay, args.sensor_operation_delay)
    aqi_2_5, aqi_10 = conv_aqi(pmt_2_5, pmt_10)

    color_aqi_2_5 = get_aqi_color(aqi_2_5)
    color_aqi_10 = get_aqi_color(aqi_10)

    # Set Turris Omnia User #1 and #2 LED colors
    if args.omnia_leds is True:
        set_turris_omnia_led(color_aqi_2_5, color_aqi_10)

    if args.log is not None:
        # A log file was given
        save_log(args.log, pmt_2_5, aqi_2_5, pmt_10, aqi_10)

    # Wait before taking the next measure with the sensor
    time.sleep(args.delay)
