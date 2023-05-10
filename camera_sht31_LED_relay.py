import os
import time
import board
import busio
import adafruit_sht31d
import RPi.GPIO as GPIO
import csv
import datetime
from picamera2 import Picamera2, Preview

# Define bounds across temperature and humidity
temperature_bounds = (22,25)
humidity_bounds = (70,75)

# Set intervals for capturing temperature/humidity and pictures
capture_interval_sht31 = 5  # Capture SHT31 data every x seconds
capture_interval_picture = 10  # Capture a picture every x seconds

# Define the pins
heater_pin = 20
humidity_pin = 21
led_pin = 22

# Set up GPIO pins for relays
GPIO.setmode(GPIO.BCM)
GPIO.setup(heater_pin, GPIO.OUT)  # Relay 1
GPIO.setup(humidity_pin, GPIO.OUT)  # Relay 2
GPIO.setup(led_pin, GPIO.OUT)  # Relay 3

# Turn off heater, humidifier and LED initially
GPIO.output(heater_pin, GPIO.LOW)
GPIO.output(humidity_pin, GPIO.LOW)
GPIO.output(led_pin, GPIO.LOW)

# Set up SHT31D sensor
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_sht31d.SHT31D(i2c)

# Set up Picamera2
piCam = Picamera2()
dispW = 1980
dispH = 1080
piCam_config = piCam.create_still_configuration(main={"size": (dispW, dispH)},
                                                 lores={"size": (640, 480)},
                                                 display="lores")
piCam.configure(piCam_config)
piCam.start_preview(Preview.QTGL)
piCam.start()

# Define CSV file path and picturesMOSFET directory
csv_path = "/media/sdcard/Data/data.csv"
pictures_directory = "/media/sdcard/Pictures/"

# Function to write data to CSV file
def write_data_to_csv(file_path, data):
    with open(file_path, mode='a', newline='') as data_file:
        data_writer = csv.writer(data_file)
        data_writer.writerow(data)

# Check if the CSV file exists, if not, create a header row
if not os.path.exists(csv_path):
    write_data_to_csv(csv_path, ['datetime', 'temperature', 'humidity'])

# Set up the day-night cycle
day_hours = 16
night_hours = 8
day_start_time = datetime.time(hour=6)
night_start_time = datetime.time(hour=22)

# Define a function to determine if it is currently day or night
def is_day():
    now = datetime.datetime.now().time()
    if now >= day_start_time and now < night_start_time:
        return True
    else:
        return False

elapsed_seconds = 0

with open(csv_path, mode='a', newline='') as data_file:
    data_writer = csv.writer(data_file)

    # Check if the file is new and write the header row
    if data_file.tell() == 0:
        data_writer.writerow(['datetime', 'temperature', 'humidity'])
        print("New CSV file created.")
    else:
        print("Old CSV file opened.")
    while True:
        # Read temperature and humidity data
        temp = sensor.temperature
        hum = sensor.relative_humidity
        print(f"Temperature: {temp:.2f}°C, Humidity: {hum:.2f}%")
        
        # Control heater and humidifier based on temperature and humidity bounds
        if temp < temperature_bounds[0]:
            GPIO.output(heater_pin, GPIO.HIGH)
        elif temp > temperature_bounds[1]:
            GPIO.output(heater_pin, GPIO.LOW)

        if hum < humidity_bounds[0]:
            GPIO.output(humidity_pin, GPIO.HIGH)
        elif hum > humidity_bounds[1]:
            GPIO.output(humidity_pin, GPIO.LOW)

        # Control LEDs based on day-night cycle
        if is_day():
            GPIO.output(led_pin, GPIO.HIGH)
        else:
            GPIO.output(led_pin, GPIO.LOW)

        # Print state of relays
        print("Heater is", "on" if GPIO.input(heater_pin) == GPIO.HIGH else "off")
        print("Humidifier is", "on" if GPIO.input(humidity_pin) == GPIO.HIGH else "off")
        print("LEDs are", "on" if GPIO.input(led_pin) == GPIO.HIGH else "off")

        # Check if it's time to capture a picture
        if elapsed_seconds % capture_interval_picture == 0:
            formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            picture_file_path = os.path.join(pictures_directory, f"{formatted_datetime}.jpg")
            piCam.capture_file(picture_file_path)
        
        # Check if it's time to capture temperature/humidity data
        if elapsed_seconds % capture_interval_sht31 == 0:
            print(f"Temperature: {temp:.2f}°C, Humidity: {hum:.2f}%")
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            write_data_to_csv(csv_path, [current_time, f"{temp:.2f}", f"{hum:.2f}"])

        # Sleep for 1 second and increment elapsed_seconds
        time.sleep(1)
        elapsed_seconds += 1

        # Check if the day-night cycle needs to be updated
        if elapsed_seconds % 3600 == 0:  # check every hour
            if is_day():
                night_start_time = (datetime.datetime.combine(datetime.date.min, datetime.datetime.now().time()) + datetime.timedelta(hours=day_hours)).time()
            else:
                day_start_time = (datetime.datetime.combine(datetime.date.min, datetime.datetime.now().time()) + datetime.timedelta(hours=night_hours)).time()

