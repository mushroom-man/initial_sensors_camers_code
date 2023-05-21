import os
import time
import board
import busio
import adafruit_sht31d
import RPi.GPIO as GPIO
import csv
import datetime

# Define bounds across temperature and humidity
temperature_bounds = (22, 25)
humidity_bounds = (70, 75)

# Set intervals for capturing temperature/humidity
capture_interval_sht31 = 5  # Capture SHT31 data every x seconds

# Define the pins
heater_pin = 20
humidity_pin = 21
led_pin = 22
fan_pin = 23

# Set up GPIO pins for relays
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(heater_pin, GPIO.OUT)  # Relay 1
    GPIO.setup(humidity_pin, GPIO.OUT)  # Relay 2
    GPIO.setup(led_pin, GPIO.OUT)  # Relay 3
    GPIO.setup(fan_pin, GPIO.OUT)  # Relay 4

    # Turn off heater, humidifier, and LED initially
    GPIO.output(heater_pin, GPIO.LOW)
    GPIO.output(humidity_pin, GPIO.LOW)
    GPIO.output(led_pin, GPIO.LOW)
    GPIO.output(fan_pin, GPIO.LOW)
except Exception as e:
    print(f"Error setting up GPIO: {e}")

# Set up SHT31D sensor
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_sht31d.SHT31D(i2c)
except Exception as e:
    print(f"Error setting up SHT31D sensor: {e}")

# Define CSV file path
csv_path = "/media/johnhenry/125GBVolume/Data/data.csv"

# Function to write data to CSV file
def write_data_to_csv(file_path, data):
    try:
        # Extract the directory from the file_path
        directory = os.path.dirname(file_path)
        
        # If the directory does not exist, create it
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, mode='a', newline='') as data_file:
            data_writer = csv.writer(data_file)
            data_writer.writerow(data)
    except Exception as e:
        print(f"Error writing data to CSV: {e}")

# Check if the CSV file exists, if not, create a header row
try:
    if not os.path.exists(csv_path):
        write_data_to_csv(csv_path, ['datetime', 'temperature', 'humidity', 'led_state', 'fan_state'])
except Exception as e:
    print(f"Error checking CSV file: {e}")

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

# Open CSV file
try:
    with open(csv_path, mode='a', newline='') as data_file:
        data_writer = csv.writer(data_file)

        # Check if the file is new and write the header row
        if data_file.tell() == 0:
            data_writer.writerow(['datetime', 'temperature', 'humidity', 'led_state', 'fan_state'])
            print("New CSV file created.")
        else:
            print("Old CSV file opened.")

        while True:
            # Read temperature and humidity data
            try:
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

                # Check if it's time to capture temperature/humidity data
                if elapsed_seconds % capture_interval_sht31 == 0:
                    print(f"Temperature: {temp:.2f}°C, Humidity: {hum:.2f}%")

                    # Capture LED and fan states
                    led_state = GPIO.input(led_pin)
                    fan_state = GPIO.input(fan_pin)

                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    write_data_to_csv(csv_path, [current_time, f"{temp:.2f}", f"{hum:.2f}", led_state, fan_state])


                # Sleep for 1 second and increment elapsed_seconds
                time.sleep(0.5)
                elapsed_seconds += 1

                # Check if the day-night cycle needs to be updated
                if elapsed_seconds % 3600 == 0:  # check every hour
                    if is_day():
                        night_start_time = (
                            datetime.datetime.combine(datetime.date.min, datetime.datetime.now().time())
                            + datetime.timedelta(hours=day_hours)
                        ).time()
                    else:
                        day_start_time = (
                            datetime.datetime.combine(datetime.date.min, datetime.datetime.now().time())
                            + datetime.timedelta(hours=night_hours)
                        ).time()

            except Exception as e:
                print(f"Error reading sensor data: {e}")

except Exception as e:
    print(f"Error opening CSV file: {e}")

finally:
    # Clean up GPIO settings
    try:
        GPIO.cleanup()
    except Exception as e:
        print(f"Error cleaning up GPIO: {e}")
