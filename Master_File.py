import os
import time
import board
import busio
import adafruit_sht31d
import RPi.GPIO as GPIO
import csv
import datetime
from picamera2 import Picamera2, Preview


########################################################
# Set up Picamera2
def setup_camera():
    piCam = Picamera2()
    dispW = 1980
    dispH = 1080
    piCam_config = piCam.create_still_configuration(main={"size": (dispW, dispH)},
                                                     lores={"size": (640, 480)},
                                                     display="lores")
    piCam.configure(piCam_config)
    piCam.start_preview(Preview.QTGL)
    piCam.start()
    return piCam

piCam = setup_camera()

def capture_picture(piCam, pictures_directory):
    formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    picture_file_path = os.path.join(pictures_directory, f"{formatted_datetime}.jpg")
    piCam.capture_file(picture_file_path)

##################################################
# Set up SHT31D sensor
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_sht31d.SHT31D(i2c)

# The SH31 sensor collects temperature and humidity
# Set intervals for capturing temperature/humidity/LED and pictures
capture_interval_sht31 = 5  # Capture SHT31 data every x seconds
capture_interval_picture = 10  # Capture a picture every x seconds

# We will set the bounds for these sensors. Bounds define the range what we will allow
# fluctuation. 
temperature_bounds = (22,25)
humidity_bounds = (70,75)

############################################
# Controlling the LEDs
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
led_state = 0  # Initialize LED state to off

######################################################
# Controlling the fan
# Define the inputs
CMH = 680    # flow rate in cubic meters per hour
L = 1.8        # length of the chamber in meters
W = 1.4        # width of the chamber in meters
B = 2        # height of the chamber in meters
n = 8        # number of air changes per hour

# Calculate the flow rate in cubic meters per second
x = 3600     # number of seconds in an hour
CMS = CMH / x

# Calculate the air change rate in seconds
CS = L * W * B  # chamber size in cubic meters
print(f"The chamber size is {CS:.2f} meters cubed.")
y = CS / CMS
print(f"The time interval when the fan is on {y:.2f} seconds.")

# Calculate the time interval between turning the fan on and off
interval = x / n
print(f"The time interval between fan on/off is {interval:.2f} seconds.")

###############################################
# GPIO pin set-up
# Define the pins
heater_pin = 20
humidity_pin = 21
led_pin = 22
fan_pin = 23

# Set up GPIO pins for relays
GPIO.setmode(GPIO.BCM)
GPIO.setup(heater_pin, GPIO.OUT)  # Relay 1
GPIO.setup(humidity_pin, GPIO.OUT)  # Relay 2
GPIO.setup(led_pin, GPIO.OUT)  # Relay 3
GPIO.setup(fan_pin, GPIO.OUT) # Relay 4

# Turn off heater, humidifier, LED initially
GPIO.output(heater_pin, GPIO.LOW)
GPIO.output(humidity_pin, GPIO.LOW)
GPIO.output(led_pin, GPIO.LOW)
GPIO.setup(fan_pin, GPIO.LOW)

################################################################
# Writing data to CSV
# Define CSV file path and picturesMOSFET directory
csv_path = "/media/sdcard/Data/data.csv"
pictures_directory = "/media/sdcard/Pictures/"

# Function to write data to CSV file
def write_data_to_csv(file_path, data):
    with open(file_path, mode='a', newline='') as data_file:
        data_writer = csv.writer(data_file)
        data_writer.writerow(data)

if not os.path.exists(csv_path):
    write_data_to_csv(csv_path, ['datetime', 'temperature', 'humidity', 'led_state'])

# This will run continuously
while True:
    # Get the current time
    current_time = datetime.datetime.now()
    
    # Capture temperature and humidity data
    if elapsed_seconds % capture_interval_sht31 == 0:
        temperature = sensor.temperature
        humidity = sensor.relative_humidity
        # Control temperature
        if temperature < temperature_bounds[0]:
            GPIO.output(heater_pin, GPIO.HIGH)  # Turn heater on
        elif temperature > temperature_bounds[1]:
            GPIO.output(heater_pin, GPIO.LOW)   # Turn heater off
        
        # Control humidity
        if humidity < humidity_bounds[0]:
            GPIO.output(humidity_pin, GPIO.HIGH)  # Turn humidifier on
        elif humidity > humidity_bounds[1]:
            GPIO.output(humidity_pin, GPIO.LOW)   # Turn humidifier off
        
        # Write the data to the CSV file
        write_data_to_csv(csv_path, [current_time, temperature, humidity, led_state])

        # Control LED
    if is_day():
        GPIO.output(led_pin, GPIO.HIGH)  # Turn LED on
        led_state = 1
    else:
        GPIO.output(led_pin, GPIO.LOW)  # Turn LED off
        led_state = 0

    # Control Fan
    if elapsed_seconds % interval == 0:
        GPIO.output(fan_pin, GPIO.HIGH)  # Turn fan on
    else:
        GPIO.output(fan_pin, GPIO.LOW)  # Turn fan off

    # Capture picture
    # if elapsed_seconds % capture_interval_picture == 0:
    #    picture_file_path = os.path.join(pictures_directory, f"{current_time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg")
    #    piCam.take_picture(picture_file_path)
        
    if elapsed_seconds % capture_interval_picture == 0:
        capture_picture(piCam, pictures_directory)

    # Increment the elapsed time
    elapsed_seconds += 1

    # Sleep for one second
    time.sleep(1)

# Remember to cleanup GPIO before ending the program
GPIO.cleanup()

