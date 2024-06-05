USE energy_data;
CREATE TABLE tasmota_mqtt (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Voltage FLOAT,
    Current FLOAT,
    Power FLOAT,
    Total FLOAT,
    PowerFactor FLOAT,
    PowerState VARCHAR(10),
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE tasmota_mqtt ADD COLUMN MessageID VARCHAR(255);
-- ALTER TABLE tasmota_mqtt
-- ADD UNIQUE (MessageID);
