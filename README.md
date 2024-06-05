# Automatically-turn-off-the-3D-printer
Automatic 3D printer shutdown system and storage of energy usage data in database

# IOT Class Project

This project is part of an IoT class, demonstrating how to collect data from multiple smart plugs and store it in a MySQL database using Flask and Python. The data sent by the smart plugs via MQTT includes Voltage, Current, Power, and Total energy consumption.

## Project Structure

- `db_to_mqtt_graph_flask.py`: Main Flask application that serves the web interface and handles data visualization.
- `sub_mqtt_sql.py`: Script to subscribe to MQTT topics and store the incoming data into the MySQL database.
- `energy_data.sql`: SQL script to create the necessary database and tables.
- `static`: Directory containing static files (e.g., CSS, JavaScript).
- `style.css`: CSS file for styling the web interface.
- `templates`: Directory containing HTML templates for the web interface.

## Installation

1. Clone this repository:
    ```bash
    git clone https://github.com/your-username/your-repository.git
    cd your-repository
    ```

2. Create a virtual environment and activate it:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Set up the MySQL database:
    ```bash
    mysql -u your-username -p < energy_data.sql
    ```

5. Update the database connection details in `db_to_mqtt_graph_flask.py` and `sub_mqtt_sql.py`.

## Usage

1. Run the Flask application:
    ```bash
    python db_to_mqtt_graph_flask.py
    ```

2. Run the MQTT subscriber script:
    ```bash
    python sub_mqtt_sql.py
    ```
