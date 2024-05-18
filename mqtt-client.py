#!/usr/bin/env python3
import json
import paho.mqtt.client as mqtt
import os
import subprocess
import psutil
import time
from threading import Thread

# MQTT broker details
MQTT_BROKER = "your ip"  # Change to your MQTT broker's IP address
MQTT_PORT = 1883
# MQTT broker authentication credentials
MQTT_USERNAME = "your username"
MQTT_PASSWORD = "your password" #change this to your password
# Unique identifier for the device
DEVICE_ID = "smart_mirror"


# Topic settings
STATE_TOPIC = f"homeassistant/switch/{DEVICE_ID}/state"
COMMAND_TOPIC = f"homeassistant/switch/{DEVICE_ID}/set"
DISPLAY_TOPIC = f"homeassistant/switch/{DEVICE_ID}/display/set"
FIREFOX_TOPIC = f"homeassistant/switch/{DEVICE_ID}/firefox/set"
REBOOT_TOPIC = f"homeassistant/switch/{DEVICE_ID}/reboot/set"
DISPLAY_STATE_TOPIC = f"homeassistant/switch/{DEVICE_ID}/display/state"
FIREFOX_STATE_TOPIC = f"homeassistant/switch/{DEVICE_ID}/firefox/state"

CPU_USAGE_TOPIC = f"homeassistant/sensor/{DEVICE_ID}/cpu_usage/state"
MEMORY_USAGE_TOPIC = f"homeassistant/sensor/{DEVICE_ID}/memory_usage/state"
TEMPERATURE_TOPIC = f"homeassistant/sensor/{DEVICE_ID}/temperature/state"

# Callback functions
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(COMMAND_TOPIC)
        client.subscribe(DISPLAY_TOPIC)
        client.subscribe(FIREFOX_TOPIC)
        client.subscribe(REBOOT_TOPIC)
        announce_device(client)
    else:
        print(f"Failed to connect to MQTT broker with return code {rc}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Received message: {payload} on topic {msg.topic}")

    if msg.topic == COMMAND_TOPIC:
        if payload == "ON":
            execute_action(client, turn_on_mirror, "ON", STATE_TOPIC)
        elif payload == "OFF":
            execute_action(client, turn_off_mirror, "OFF", STATE_TOPIC)
    elif msg.topic == DISPLAY_TOPIC:
        if payload == "ON":
            execute_action(client, turn_on_display, "ON", DISPLAY_STATE_TOPIC)
        elif payload == "OFF":
            execute_action(client, turn_off_display, "OFF", DISPLAY_STATE_TOPIC)
    elif msg.topic == FIREFOX_TOPIC:
        if payload == "ON":
            execute_action(client, start_firefox, "ON", FIREFOX_STATE_TOPIC)
        elif payload == "OFF":
            execute_action(client, kill_firefox, "OFF", FIREFOX_STATE_TOPIC)
    elif msg.topic == REBOOT_TOPIC:
        execute_action(client, reboot_pi, None)

def on_disconnect(client, userdata, rc):
    print(f"Disconnected from MQTT broker with return code {rc}")

# Generic function to handle actions and state updates
def execute_action(client, action_func, state, state_topic=None):
    try:
        action_func()
        if state is not None and state_topic is not None:
            client.publish(state_topic, state, retain=True)
    except Exception as e:
        print(f"Error executing action: {e}")

# Functions to control the mirror
def turn_on_mirror():
    print("Turning on the mirror")
    # Insert code to turn on the mirror here

def turn_off_mirror():
    print("Turning off the mirror")
    # Insert code to turn off the mirror here

# Functions for additional controls
def run_script(script_name):
    try:
        subprocess.call([f'/home/pi/scripts/{script_name}.sh'])
    except FileNotFoundError:
        print(f"Script {script_name}.sh not found.")
    except Exception as e:
        print(f"Error running script {script_name}: {e}")

def turn_on_display():
    print("Turning on the display")
    run_script('screen-on')

def turn_off_display():
    print("Turning off the display")
    run_script('screen-off')

def reboot_pi():
    print("Rebooting the Raspberry Pi")
    run_script('reboot')

def kill_firefox():
    print("Killing Firefox")
    run_script('kill-firefox')

def start_firefox():
    print("Starting Firefox")
    run_script('start-HA-Firefox-kiosk')

def create_and_publish_config(client, name, command_topic, state_topic, unique_id):
    config_payload = {
        "name": name,
        "command_topic": command_topic,
        "state_topic": state_topic,
        "availability_topic": f"homeassistant/switch/{DEVICE_ID}/availability",
        "payload_on": "ON",
        "payload_off": "OFF",
        "unique_id": unique_id,
        "device": {
            "identifiers": [DEVICE_ID],
            "name": "Smart Mirror",
            "model": "Raspberry Pi Smart Mirror",
            "manufacturer": "<your name> Mirroracle Innovations Ltd."
        }
    }
    client.publish(f"homeassistant/switch/{unique_id}/config", json.dumps(config_payload), retain=True)

def create_and_publish_sensor_config(client, sensor_name, sensor_type, unit_of_measurement, state_topic, device_class=None, value_template=None):
    config_payload = {
        "name": sensor_name,
        "state_topic": state_topic,
        "unit_of_measurement": unit_of_measurement,
        "device": {
            "identifiers": [DEVICE_ID],
            "name": "Smart Mirror",
            "model": "Raspberry Pi Smart Mirror",
            "manufacturer": "<your name> Mirroracle Innovations Ltd."
        }
    }
    if device_class:
        config_payload["device_class"] = device_class
    if value_template:
        config_payload["value_template"] = value_template

    client.publish(f"homeassistant/sensor/{DEVICE_ID}_{sensor_name}/config", json.dumps(config_payload), retain=True)
    client.publish(state_topic, "0", retain=True)  # Initialize state to avoid missing state updates


def announce_device(client):
    create_and_publish_config(client, "Mirror Switch", COMMAND_TOPIC, STATE_TOPIC, f"{DEVICE_ID}_mirror_switch")
    create_and_publish_config(client, "Display", DISPLAY_TOPIC, DISPLAY_STATE_TOPIC, f"{DEVICE_ID}_display")
    create_and_publish_config(client, "Firefox", FIREFOX_TOPIC, FIREFOX_STATE_TOPIC, f"{DEVICE_ID}_firefox")
    create_and_publish_config(client, "Reboot Pi", REBOOT_TOPIC, "", f"{DEVICE_ID}_reboot")

    # Sensor configurations
    create_and_publish_sensor_config(client, "CPU Usage", CPU_USAGE_TOPIC, f"{DEVICE_ID}_cpu_usage", "%", "cpu")
    create_and_publish_sensor_config(client, "Memory Usage", MEMORY_USAGE_TOPIC, f"{DEVICE_ID}_memory_usage", "%", "memory")
    create_and_publish_sensor_config(client, "Temperature", TEMPERATURE_TOPIC, f"{DEVICE_ID}_temperature", "°C", "temperature")

# System metrics functions
def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_memory_usage():
    return psutil.virtual_memory().percent

def get_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0
        return temp
    except FileNotFoundError:
        print("Temperature file not found.")
        return None

def publish_system_metrics(client):
    while True:
        cpu_usage = get_cpu_usage()
        memory_usage = get_memory_usage()
        temperature = get_temperature()

        if cpu_usage is not None:
            client.publish(CPU_USAGE_TOPIC, cpu_usage, retain=True)
        if memory_usage is not None:
            client.publish(MEMORY_USAGE_TOPIC, memory_usage, retain=True)
        if temperature is not None:
            client.publish(TEMPERATURE_TOPIC, temperature, retain=True)

        time.sleep(60)  # Adjust the interval as needed

# Main function
def main():
    client = mqtt.Client(client_id=DEVICE_ID)  # Use MQTT v3.1.1 by default
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start the system metrics publishing thread
    metrics_thread = Thread(target=publish_system_metrics, args=(client,))
    metrics_thread.daemon = True
    metrics_thread.start()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Disconnecting from MQTT broker")
        client.disconnect()

if __name__ == "__main__":
    main()