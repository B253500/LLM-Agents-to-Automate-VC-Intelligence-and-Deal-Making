
import sqlite3
import json
import os

def extract_workflows():
    db_path = 'n8n/data/database.sqlite'
    output_dir = 'n8n/workflows'

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()

        # Get all workflows
        cur.execute("SELECT name, active, nodes, settings, staticData FROM workflow_entity")
        workflows = cur.fetchall()

        if not workflows:
            print("No workflows found in the database.")
            return

        for name, active, nodes, settings, static_data in workflows:
            workflow_data = {
                "name": name,
                "active": active,
                "nodes": json.loads(nodes),
                "settings": json.loads(settings),
                "staticData": static_data,
            }

            # Sanitize the workflow name to create a valid filename
            safe_filename = "".join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip()
            safe_filename = safe_filename.replace(' ', '_').lower() + '.json'
            output_path = os.path.join(output_dir, safe_filename)

            with open(output_path, 'w') as f:
                json.dump(workflow_data, f, indent=2)

            print(f"Successfully extracted workflow: {name} -> {output_path}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if con:
            con.close()

if __name__ == '__main__':
    extract_workflows()
