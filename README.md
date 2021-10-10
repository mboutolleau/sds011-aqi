# sds011-aqi

Measure ambient air quality using an SDS011 sensor on GNU/Linux. 

This sensor can retrieve the current PM2.5 (particles less than or equal to 2.5 micrometers) and PM10 (particles less than or equal to 10 micrometers) levels and compute an [AQI index](https://en.wikipedia.org/wiki/Air_quality_index). Currently, three AQI indexes are supported : European Union (CAQI), Mainland China and United States of America. Measured data can be logged to a CSV file.

Designed to run on a [Turis Omnia](https://www.turris.com/en/omnia/overview/), this tool can optionally set the color of the device's LED to visualize the air quality.

The code is heavily inspired by Marcelo Rovai and his excellent blog post https://www.instructables.com/A-Low-cost-IoT-Air-Quality-Monitor-Based-on-Raspbe/.

## Dependencies

- [`py-sds011`](https://pypi.org/project/py-sds011/) (Interface to the SDS011 sensor)
- [`pyserial`](https://pypi.org/project/pyserial/) (Library for serial communication, required by `py-sds011`)
- [`aqipy-atmotech`](https://pypi.org/project/aqipy-atmotech/) (Library to convert between AQI value and pollutant concentration)

To use the sensor, on OpenWRT, via its USB-Serial adapter :

- [`kmod-usb-serial-ch341`](https://openwrt.org/packages/pkgdata/kmod-usb-serial-ch341) (OpenWRT kernel module for the HL-340 USB-Serial adapter used by the sensor)

## Installation

Use [`pip`](https://packaging.python.org/tutorials/installing-packages/) to install the required libraries from PyPI :

```
$ pip3 install py-sds011 pyserial aqipy-atmotech
```

On OpenWRT, you will need to install a kernel module to use the sensor :

```
opkg update
opkg install kmod-usb-serial-ch341
```

Clone the repository :

```
git clone https://github.com/mboutolleau/sds011-aqi.git
```

## Usage

Connect a SDS011 sensor and run `get_aqi.py` to start measurements, this example will use the sensor available at `/dev/ttyUSB0` and append data to the `aqi.csv` CSV file :

```
$ ./get_aqi.py --log aqi.csv --sensor /dev/ttyUSB0
```

Run with the `-h` flag to get the help text :

```
$ ./get_aqi.py -h
usage: get_aqi.py [-h] [--country COUNTRY] [--delay SECONDS] [--log FILE]
                  [--measures N] [--omnia-leds] [--sensor FILE]
                  [--sensor-operation-delay SECONDS]
                  [--sensor-start-delay SECONDS]

Measure air quality using an SDS011 sensor.

optional arguments:
  -h, --help            show this help message and exit
  --country COUNTRY, -c COUNTRY
                        country code (ISO 3166-1 alpha-2) used to compute AQI.
                        Currently accepted values (default: EU) : 'CN' (AQI
                        Mainland China), 'EU' (CAQI) and 'US' (AQI US)
  --delay SECONDS, -d SECONDS
                        seconds to pause after getting data with the sensor
                        before taking another measure (default: 1200, ie. 20
                        minutes)
  --log FILE, -l FILE   path to the CSV file where data will be appended
  --measures N, -m N    get PM2.5 and PM10 values by taking N consecutive
                        measures (default: 3)
  --omnia-leds, -o      set Turris Omnia LED colors according to measures
                        (User #1 LED for PM2.5 and User #2 LED for PM10)
  --sensor FILE, -s FILE
                        path to the SDS011 sensor (default: '/dev/ttyUSB0')
  --sensor-operation-delay SECONDS, -p SECONDS
                        seconds to let the sensor start (default: 10)
  --sensor-start-delay SECONDS, -t SECONDS
                        seconds to let the sensor perform an operation :
                        taking a measure or going to sleep (default: 1)
```
