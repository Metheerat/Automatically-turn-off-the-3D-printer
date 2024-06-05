import threading
import time
import mysql.connector
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import paho.mqtt.publish as publish

app = Flask(__name__)

MQTT_BROKER = "172.30.85.182"

# Initialize the energy data dictionary
graph_energy_data = {
    "today": [0] * 24,
    "week": [0] * 5,
    "monthly": [0] * 12,
    "yearly": [0] * 3
}

# Database configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'iot',
    'raise_on_warnings': True
}

valid_tokens = set()

# Store the accumulated energy for display when device is OFF
display_energy = None

def continuous_polling():
    global graph_energy_data, display_energy
    tracking = False
    accumulated_energy = 0
    start_time = None
    low_power_start_time = None

    while True:
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM iot.tasmota_mqtt ORDER BY Timestamp DESC LIMIT 1;")
            row = cursor.fetchone()
            if row:
                power = float(row[2])  # Get the power value
                timestamp = row[5]  # Get the timestamp
                device_state = row[4]  # Get the device state

                if device_state == "ON" and power > 50:
                    if not tracking:
                        tracking = True
                        start_time = timestamp
                        accumulated_energy = 0
                    accumulated_energy += (power * 60) / 3600000  # Convert to kWh assuming readings every 60 seconds
                    low_power_start_time = None
                    display_energy = None  # Reset display energy when the device is ON
                elif device_state == "OFF" or power < 50:
                    if tracking:
                        if low_power_start_time is None:
                            low_power_start_time = timestamp
                        elif timestamp - low_power_start_time >= timedelta(minutes=5):
                            update_graph_energy_data(accumulated_energy)
                            display_energy = accumulated_energy
                            print(f"Accumulated energy: {accumulated_energy} kWh")
                            tracking = False
                            low_power_start_time = None

            cursor.close()
            conn.close()
            time.sleep(60)  # Fetch data every 60 seconds
        except Exception as e:
            print(f"Error in polling loop: {e}")
        finally:
            if conn.is_connected():
                conn.close()

def update_graph_energy_data(total_energy):
    now = datetime.now()
    hour_block = now.hour // 2  # Group into 2-hour blocks
    graph_energy_data["today"][hour_block] += total_energy
    print(f"Updated energy for 2-hour block {hour_block * 2}-{(hour_block + 1) * 2}: {graph_energy_data['today'][hour_block]} kWh")



@app.route('/toggle_mqtt', methods=['POST'])
def handle_toggle():
    data = request.get_json()
    send_mqtt_command(data['command'])
    return jsonify({'status': 'Command sent successfully'})

@app.route('/', methods=['GET', 'POST'])
def index():
    token = request.args.get('token')
    if token in valid_tokens:
        return render_template("index.html")
    else:
        return redirect(url_for('unauthorized'))

@app.route('/historical')
def historical():
    return render_template("historical_graph.html")

@app.route('/unauthorized')
def unauthorized():
    return "Unauthorized access", 403

@app.route('/verify_token', methods=['POST'])
def verify_token():
    token = request.form.get('token')
    if token:
        valid_tokens.add(token)
        return 'Token verified'
    else:
        return 'Invalid token', 400

@app.route('/monitoring')
def monitoring():
    return render_template("graph.html")

@app.route("/data/<string:period>")
def get_data(period):
    if period in graph_energy_data:
        data = [
            {'timestamp': (datetime.now() - timedelta(hours=i)).strftime('%H:%M:%S'), 'power': val}
            for i, val in enumerate(graph_energy_data[period][::-1])
        ]
        return jsonify(data)
    return "Invalid period", 404

@app.route('/data/today')
def get_today_data():
    now = datetime.now()
    start_of_day = datetime.combine(now, datetime.min.time())
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = """
        SELECT HOUR(Timestamp), AVG(Power) 
        FROM iot.tasmota_mqtt 
        WHERE Timestamp BETWEEN %s AND %s 
        GROUP BY HOUR(Timestamp)
        ORDER BY HOUR(Timestamp)
    """
    cursor.execute(query, (start_of_day, now))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    data = [{'timestamp': (datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=row[0])).strftime('%Y-%m-%dT%H:%M:%S'), 'power': row[1]} for row in rows]
    return jsonify(data)


@app.route('/data/latest')
def get_latest_data():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT Voltage, Current, Power, Total, PowerState, Timestamp FROM iot.tasmota_mqtt ORDER BY Timestamp DESC LIMIT 1;")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        total_energy = row[2]
        data = {
            'voltage': row[0],
            'current': row[1],
            'power': total_energy,
            'total': row[3],
            'state': row[4],
            'timestamp': row[5].strftime('%Y-%m-%dT%H:%M:%S')
        }
        return jsonify(data)
    else:
        return jsonify({'error': 'No data available'}), 404


@app.route('/data/range')
def get_data_range():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if not start_date or not end_date:
        return "Invalid date range", 400
    
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    query = """
        SELECT Timestamp, Power 
        FROM iot.tasmota_mqtt 
        WHERE Timestamp BETWEEN %s AND %s 
        ORDER BY Timestamp
    """
    cursor.execute(query, (start_datetime, end_datetime))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    total_energy_kwh = sum((row[1] * (10 / 3600)) / 1000 for row in rows)  # Convert watt to kWh using 10-second intervals

    data = {
        'total_energy_kwh': total_energy_kwh,
        'details': [{'timestamp': row[0].strftime('%Y-%m-%dT%H:%M:%S'), 'power': row[1]} for row in rows]
    }
    
    return jsonify(data)




@app.route('/printer_status')
def get_printer_status():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT Power FROM iot.tasmota_mqtt ORDER BY Timestamp DESC LIMIT 1;")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        power = float(row[0])
        status = "Unknown"
        if power < 5:
            status = "IDLE"
        elif power < 50:
            status = "Countdown"
        else:
            status = "Working"
        return jsonify({'power': power, 'status': status})
    else:
        return jsonify({'error': 'No data available'}), 404

def send_mqtt_command(command):
    print(command)
    topic = "cmnd/tasmota_01/Power"  # Use a fixed topic
    print(f"Sending MQTT Command: {command} to Topic: {topic}")
    publish.single(topic, command, hostname=MQTT_BROKER)  # Ensure hostname points to your MQTT broker

@app.route('/logout')
def logout():
    # Perform any necessary cleanup
    session.clear()
    return redirect('http://localhost/logout.php')  # URL ของ logout.php

if __name__ == "__main__":
    # Start the background thread
    thread = threading.Thread(target=continuous_polling)
    thread.daemon = True  # This thread will automatically close when the main program exits
    thread.start()
    
    # Run the Flask app
    app.run(debug=True)
