import sqlite3
conn = sqlite3.connect('c:/Users/Alisha/Desktop/Agri_another/Agriculture-data-ML-Based-Attack-Detection/backend/agri_iot.db')
conn.execute('UPDATE devices SET device_type="soil_moisture" WHERE device_type="sensor"')
conn.commit()
