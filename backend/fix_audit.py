import sqlite3
import json

conn = sqlite3.connect('c:/Users/Alisha/Desktop/Agri_another/Agriculture-data-ML-Based-Attack-Detection/backend/agri_iot.db')
cursor = conn.cursor()

# Get all audit logs
cursor.execute("SELECT id, event_details FROM audit_logs")
rows = cursor.fetchall()

fixed = 0
for row_id, details in rows:
    try:
        # Check if details is a string instead of JSON object
        if isinstance(details, str) and details.startswith('"'):
            parsed = json.loads(details)
            if isinstance(parsed, str):
                new_details = json.dumps({"reason": parsed})
                cursor.execute("UPDATE audit_logs SET event_details = ? WHERE id = ?", (new_details, row_id))
                fixed += 1
        elif isinstance(details, str) and not details.startswith('{') and not details.startswith('['):
            new_details = json.dumps({"reason": details})
            cursor.execute("UPDATE audit_logs SET event_details = ? WHERE id = ?", (new_details, row_id))
            fixed += 1
    except Exception as e:
        print(f"Error row {row_id}: {e}")

conn.commit()
conn.close()
print(f"Fixed {fixed} corrupted audit logs.")
