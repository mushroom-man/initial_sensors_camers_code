import RPi.GPIO as GPIO
import time

# Set up the GPIO pin for the fan
fan_pin = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(fan_pin, GPIO.OUT)

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

# Run the fan at the required interval and air change rate
try:
    while True:
        # Turn the fan on
        GPIO.output(fan_pin, GPIO.HIGH)
        print("Fan turned on.")
        time.sleep(y)   # Wait for the required air change rate
        
        # Turn the fan off
        GPIO.output(fan_pin, GPIO.LOW)
        print("Fan turned off.")
        time.sleep(interval - y)  # Wait for the remaining time in the interval
except KeyboardInterrupt:
    # Clean up the GPIO settings
    GPIO.cleanup()
