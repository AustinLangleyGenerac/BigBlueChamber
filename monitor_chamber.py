# Developer only -- TEST MODE
# Uses fake Big Blue class to test script
TEST = 0

if (TEST):
    from lib import fake_bb as tc
else:
    from lib import thermal_chamber as tc
    
import sys
import csv
import time
from datetime import datetime, timedelta

# Get COM port from user
port = sys.argv[1]

# Keep count of number of samples
sample_count = 0

# Query the user for time to run and interval to collect data
try:
    interval = int(input("Enter the time (in seconds) between each sample: "))
    if (interval < 1) or (interval > 60):
        raise Exception('Invalid interval. Value must be between 1 and 60. Setting interval to 10 seconds.')
except Exception as error:
    interval = 10
    print(error)

try:
    run_time = float(input("Enter the time (in hours) that you would like the script to run: "))
    if (run_time < 0.1) or (run_time > 24):
        raise Exception('Invalid run time. Value must be between 0.1 and 12. Setting interval to 1 hour.')
except Exception as error:
    run_time = 1
    print(error)

# Connect to big blue
if (TEST):
    print("TEST MODE")
else:
    print("Attempting to connect to Big Blue on port " + port)

try:
    if (TEST):
        bigBlue = tc.BigBlue()
    else:
        bigBlue = tc.BigBlue(port)
except:
    print("Could not connect to Big Blue. Check your connections and that you selected the correct COM port.")
    exit()

# bigBlue = tc.BigBlue(port)

if (not TEST):
    print("Connected")

# Get start date/time
start_time = datetime.now()

# Variable to store temp and humidity data in
data = []

hours = int(run_time)
minutes = int((run_time - hours) * 60)
print(f"Script will now run for {hours} hours and {minutes} minutes. To cancel, press CTRL+C")

while True:
    # get current and elapsed time and exit loop when time is up
    current_time = datetime.now()
    current_time_formatted = f"{current_time.hour}:{current_time.minute}:{current_time.second}"
    elapsed_time = current_time - start_time
    percent_complete = (elapsed_time / timedelta(hours=run_time)) * 100
    if elapsed_time >= timedelta(hours=run_time):
        break

    # Print percent complete with test
    print(f"{percent_complete:.3}% Complete")

    # Read Big Blue data
    temp = bigBlue.read_temp()
    humidity = bigBlue.read_humidity()
    temp_sp = bigBlue.read_temp_setpoint()
    humidity_sp = bigBlue.read_humidity_setpoint()

    data.append({'timestamp': current_time_formatted, 'temperature': temp, 'humidity': humidity, 'temp_setpoint': temp_sp, 'humidity_setpoint': humidity_sp})

    # Print data
    dt_string = f"{current_time.month}-{current_time.day}-{current_time.year} {current_time.hour}:{current_time.minute}:{current_time.second}"
    # print(f"{dt_string} -- Temperature: {temp} C, Humidity: {humidity}% -- Setpoints: Temperature: {temp_sp} C, Humidity: {humidity_sp}%")
    
    # Sleep for interval before reading again and update sample count
    sample_count = sample_count + 1
    time.sleep(interval)  

print(f"Complete. Saved {sample_count} samples in {hours} hours and {minutes} minutes.")

with open('big_blue_data.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Time", "Measured Temperature (C)", "Measured Humidity (%)", "Temperature Setpoint (C)", "Humidity Setpoint (%)"])
    for d in data:
        writer.writerow([d['timestamp'], d['temperature'], d['humidity'], d['temp_setpoint'], d['humidity_setpoint']])