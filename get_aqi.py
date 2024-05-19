#!/usr/bin/python3

import argparse
import datetime
import subprocess
import time
from collections import deque
from shutil import which

import paho.mqtt.publish
from aqipy import aqi_cn, aqi_us, caqi_eu
from sds011 import SDS011


def parse_args():
    parser = argparse.ArgumentParser(description="Measure air quality using an SDS011 sensor.")

    parser.add_argument("--country", "-c", choices=["CN", "EU", "US"], default="EU", metavar="COUNTRY", help="country code (ISO 3166-1 alpha-2) used to compute AQI. Currently accepted values (default: EU) : 'CN' (AQI Mainland China), 'EU' (CAQI) and 'US' (AQI US)")
    parser.add_argument("--delay", "-d", default=1200, metavar="SECONDS", type=int, help="seconds to pause after getting data with the sensor before taking another measure (default: 1200, ie. 20 minutes)")
    parser.add_argument("--log", "-l", metavar="FILE", help="path to the CSV file where data will be appended")
    parser.add_argument("--measures", "-m", default=3, metavar="N", type=int, help="get PM2.5 and PM10 values by taking N consecutive measures (default: 3)")
    parser.add_argument("--mqtt-hostname", "-n", metavar="IP/HOSTNAME", help="IP address or hostname of the MQTT broker")
    parser.add_argument("--mqtt-port", "-r", default="1883", metavar="PORT", type=int, help="Port number of the MQTT broker (default: '1883')")
    parser.add_argument("--mqtt-base-topic", "-i", default="aqi", metavar="TOPIC", help="Parent MQTT topic to use (default: 'aqi')")
    parser.add_argument("--omnia-leds", "-o", action="store_true", help="set Turris Omnia LED colors according to measures (User #1 LED for PM2.5 and User #2 LED for PM10)")
    parser.add_argument("--sensor", "-s", default="/dev/ttyUSB0", metavar="FILE", help="path to the SDS011 sensor (default: '/dev/ttyUSB0')")
    parser.add_argument("--sensor-operation-delay", "-p", default=1, metavar="SECONDS", type=int, help="seconds to let the sensor start (default: 10)")
    parser.add_argument("--sensor-start-delay", "-t", default=10, metavar="SECONDS", type=int, help="seconds to let the sensor perform an operation : taking a measure or going to sleep (default: 1)")

    return parser.parse_args()

def get_aqi_interval(country):
    # ISO_3166-1 country codes
    if country in ("CN", "US"):
        # 24 hours
        return 86400
    elif country in ("EU"):
        # 1 hour
        return 3600
    else:
        return -1

def get_data(sensor, measures, start_delay, operation_delay):
    # Wake-up sensor
    sensor.sleep(sleep=False)

    current_pm25 = 0.0
    current_pm10 = 0.0

    # Let the sensor at least 10 seconds to start in order to get precise values
    time.sleep(start_delay)

    # Take several measures
    for _ in range(measures):
        x = sensor.query()
        current_pm25 = current_pm25 + x[0]
        current_pm10 = current_pm10 + x[1]
        time.sleep(operation_delay)

    # Round the measures as a number with one decimal
    current_pm25 = round(current_pm25/measures, 1)
    current_pm10 = round(current_pm10/measures, 1)

    # Put the sensor to sleep
    sensor.sleep(sleep=True)
    time.sleep(operation_delay)

    return current_pm25, current_pm10

def compute_aqi(pm25, pm10, country):
    # AQI index
    current_aqi = -1
    # AQI index associated data
    current_aqi_data = {}
    # AQI index level
    current_aqi_level = ""

    # ISO_3166-1 country codes
    if country == "CN":
        current_aqi, current_aqi_data = aqi_cn.get_aqi(pm25_24h=pm25, pm10_24h=pm10)
        current_aqi, current_aqi_level = aqi_cn.get_aqi(pm25_24h=pm25, pm10_24h=pm10, with_level=True)
    elif country == "EU":
        current_aqi, current_aqi_data = caqi_eu.get_caqi(pm25_1h=pm25, pm10_1h=pm10)
        current_aqi, current_aqi_level = caqi_eu.get_caqi(pm25_1h=pm25, pm10_1h=pm10, with_level=True)
    elif country == "US":
        current_aqi, current_aqi_data = aqi_us.get_aqi(pm25_24h=pm25, pm10_24h=pm10)
        current_aqi, current_aqi_level = aqi_us.get_aqi(pm25_24h=pm25, pm10_24h=pm10, with_level=True)
    else:
        raise ValueError("Bad value: not a supported country", country)

    return current_aqi, current_aqi_data, current_aqi_level

def get_aqi_color(aqi_level, country):
    # Colors for Mainland China (AQI Mainland China)
    if country == "CN":
        if aqi_level == "excellent":
            # Green : 0 < aqi <= 50
            return "0,255,0"
        elif aqi_level == "good":
            # Yellow : 51 <= aqi <= 100
            return "255,255,0"
        elif aqi_level == "lightly polluted":
            # Orange : 101 <= aqi <= 150
            return "255,153,0"
        elif aqi_level == "moderately polluted":
            # Red : 151 <= aqi <= 200
            return "255,0,0"
        elif aqi_level == "heavily polluted":
            # Indigo : 201 <= aqi <= 299
            return "84,0,153"
        elif aqi_level == "severely polluted":
            # Maroon : aqi >= 300
            return "128,0,0"
    # Colors for Europe (CAQI), tweaked for maximum visibility
    elif country == "EU":
        if aqi_level == "very low":
            # Green : 0 < caqi <= 24
            return "0,255,0"
        elif aqi_level == "low":
            # Yellow-Green : 25 <= caqi < 49
            return "163,255,15"
        elif aqi_level == "medium":
            # Yellow : 50 <= caqi < 74
            return "255,255,0"
        elif aqi_level == "high":
            # Orange : 75 <= caqi < 99
            return "255,153,0"
        elif aqi_level == "very high":
            # Red : caqi >= 100
            return "255,0,0"
    # Colors for the United States
    elif country == "US":
        if aqi_level == "Good":
            # Green : 0 < aqi <= 50
            return "0,255,0"
        elif aqi_level == "Moderate":
            # Yellow : 51 < aqi <= 100
            return "255,255,0"
        elif aqi_level == "Unhealthy for Sensitive Groups":
            # Orange : 101 < aqi <= 150
            return "255,165,0"
        elif aqi_level == "Unhealthy":
            # Red : 151 < aqi <= 200
            return "255,0,0"
        elif aqi_level == "Very Unhealthy":
            # Purple : 201 < aqi < 300
            return "128,0,128"
        elif aqi_level == "Hazardous":
            # Maroon :  301 < aqi <= 500
            return "128,0,0"
    else:
        raise ValueError("Bad value: not a supported country", country)

def set_turris_omnia_led(user1_color, user2_color):
    if user1_color != "":
        subprocess.run(["rainbow", "indicator-1", user1_color, "enable"])

    if user2_color != "":
        subprocess.run(["rainbow", "indicator-2", user2_color, "enable"])

def save_log(logfile, logged_pm25, logged_pm10, logged_aqi):
    try:
        with open(logfile, "a") as log:
            dt = datetime.datetime.now()
            log.write("{},{},{},{}\n".format(dt, logged_pm25, logged_pm10, logged_aqi))
            log.close()
    except:
        print("[INFO] Failure in logging data")

def publish_mqtt(mqtt_hostname, mqtt_port, mqtt_messages):
    try:
        paho.mqtt.publish.multiple(mqtt_messages, hostname=mqtt_hostname, port=mqtt_port, client_id="get_aqi.py")
    except:
        print("[INFO] Failure in publishing to MQTT broker")


if __name__ == "__main__":
    args = parse_args()
    sensor = SDS011(args.sensor)

    # Time interval (in seconds) used to compute AQI values, differs by country.
    # Usually 1, 3 or 24 hours
    aqi_interval = get_aqi_interval(args.country)
    # Number of measures to take in the AQI time interval, according to --delay
    num_measures = aqi_interval // args.delay

    # If --delay > 1 AQI time interval, keep one measure instead of zero
    if num_measures <= 0:
        num_measures = 1

    # Create a PM2.5 and PM10 deques to store enough measures for the AQI time interval
    dequeue_pm25 = deque(maxlen=num_measures)
    dequeue_pm10 = deque(maxlen=num_measures)

    while(True):
        # Retrieve current PM2.5 and PM10 values from the sensor
        current_pm25, current_pm10 = get_data(sensor, args.measures, args.sensor_start_delay, args.sensor_operation_delay)

        # Append current PM2.5 and PM10 values do their respective deques,
        # discarding the oldest value if the deque if full 
        dequeue_pm25.append(current_pm25)
        dequeue_pm10.append(current_pm10)

        average_pm25 = sum(dequeue_pm25) / len(dequeue_pm25)
        average_pm10 = sum(dequeue_pm10) / len(dequeue_pm10)

        aqi, aqi_data, aqi_level = compute_aqi(average_pm25, average_pm10, args.country)

        # Set Turris Omnia User #1 and #2 LED colors if 'rainbow' command is available
        if (args.omnia_leds is True) and (which("rainbow") is not None):
            try:
                color_aqi_pm25 = get_aqi_color(aqi_level["level"], args.country)
                color_aqi_pm10 = get_aqi_color(aqi_level["level"], args.country)
            except ValueError:
                print("[ERROR] Failed to get color for AQI " + aqi_level["level"] + " and country " + args.country)
            else:
                set_turris_omnia_led(color_aqi_pm25, color_aqi_pm10)

        # Save measured values and AQI level to a log file 
        if args.log is not None:
            save_log(args.log, current_pm25, current_pm10, aqi)

        # Publish measured values and AQI level to an MQTT broker
        if args.mqtt_hostname is not None:
            # Remove any trailing '/' in topic
            topic = args.mqtt_base_topic
            if args.mqtt_base_topic.endswith("/"):
                topic = args.mqtt_base_topic.rstrip("/")

            # List of messages to publish, list of tuples.
            # The tuples are of the form ("<topic>", "<payload>", qos, retain).
            # topic must be present and may not be empty
            msg_aqi = (topic + "/aqi", str(aqi), 0, False)
            msg_level = (topic + "/level", str(aqi_level["level"]), 0, False)
            msg_current_pm25 = (topic + "/current_pm25", str(current_pm25), 0, False)
            msg_current_pm10 = (topic + "/current_pm10", str(current_pm10), 0, False)

            messages = [msg_aqi, msg_level, msg_current_pm25, msg_current_pm10]

            # Publish the messages to the MQTT broker
            publish_mqtt(args.mqtt_hostname, args.mqtt_port, messages)

        # Wait before taking the next measure with the sensor
        time.sleep(args.delay)
