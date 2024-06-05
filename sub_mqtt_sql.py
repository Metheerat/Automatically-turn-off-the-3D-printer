import paho.mqtt.client as mqtt
import mysql.connector
from mysql.connector import Error #pip install mysql-connector-python
import json
from datetime import datetime
import signal
import sys

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'iot'
}

# MQTT Configuration
# MQTT_BROKER = "100.65.164.72" # raspbery pi 400
# MQTT_BROKER = "192.168.137.97" # ASUS Notebook A
MQTT_BROKER = "172.30.85.182"

MQTT_PORT = 1883
MQTT_TOPIC_SENSOR = "tele/tasmota_01/SENSOR"
MQTT_TOPIC_STATE = "tele/tasmota_01/STATE"

# Temporary storage for messages until all parts are received
messages = {}

# Connect to MySQL Database
def connect_to_database():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None

# Insert data into MySQL
def insert_into_db(connection, query, values):
    try:
        cursor = connection.cursor()
        cursor.execute(query, values)
        connection.commit()
        print("Data inserted successfully")
    except Error as e:
        print(f"Failed to insert data into MySQL table: {e}")

# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe([(MQTT_TOPIC_SENSOR, 0), (MQTT_TOPIC_STATE, 0)])

def on_message(client, userdata, msg):
    connection = userdata
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
    except UnicodeDecodeError:
        try:
            # Try decoding as ISO-8859-1 as a fallback
            payload = json.loads(msg.payload.decode('iso-8859-1'))
        except Exception as e:
            print(f"Failed to decode payload with error: {e}")
            return
    
    message_id = datetime.now().strftime("%Y%m%d%H%M%S")

    if message_id not in messages:
        messages[message_id] = {'sensor': None, 'state': None}

    if topic == MQTT_TOPIC_SENSOR:
        messages[message_id]['sensor'] = payload['ENERGY']
    elif topic == MQTT_TOPIC_STATE:
        messages[message_id]['state'] = payload['POWER']

    if messages[message_id]['sensor'] and messages[message_id]['state']:
        energy_data = messages[message_id]['sensor']
        state_data = messages[message_id]['state']
        
        values = (message_id, energy_data['Voltage'], energy_data['Current'], energy_data['Power'],
                  energy_data['Total'], energy_data['Factor'], state_data, datetime.now())

        query = """INSERT INTO tasmota_mqtt (MessageID, Voltage, Current, Power, Total, PowerFactor, PowerState, Timestamp)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   Voltage=VALUES(Voltage), Current=VALUES(Current), Power=VALUES(Power), Total=VALUES(Total),
                   PowerFactor=VALUES(PowerFactor), PowerState=VALUES(PowerState), Timestamp=VALUES(Timestamp)"""
        insert_into_db(connection, query, values)

        print("values",values)
    
# Handle Ctrl+C
def signal_handler(sig, frame):
    print('Disconnecting gracefully')
    sys.exit(0)

# Main function
def main():
    signal.signal(signal.SIGINT, signal_handler)
    connection = connect_to_database()
    if connection:
        client = mqtt.Client(userdata=connection)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()

if __name__ == '__main__':
    main()
