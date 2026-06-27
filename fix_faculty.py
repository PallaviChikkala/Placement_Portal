import mysql.connector

def update_faculty():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Hasini@1234"
        )
        cursor = conn.cursor(dictionary=True)
        
        # We need to update all databases related to the portal
        cursor.execute("SHOW DATABASES LIKE 'placement_portal%'")
        databases = cursor.fetchall()
        
        for db in databases:
            db_name = list(db.values())[0]
            print(f"Updating database: {db_name}")
            
            cursor.execute(f"USE {db_name}")
            
            # Check if faculty table exists
            cursor.execute("SHOW TABLES LIKE 'faculty'")
            if cursor.fetchone():
                # Delete drshankar@gmail.com
                cursor.execute("DELETE FROM faculty WHERE email = 'drshankar@gmail.com'")
                
                # Check if tap@nitandhra.ac.in exists
                cursor.execute("SELECT COUNT(*) as count FROM faculty WHERE email = 'tap@nitandhra.ac.in'")
                if cursor.fetchone()['count'] == 0:
                    cursor.execute("SELECT MAX(faculty_id) as max_id FROM faculty")
                    res = cursor.fetchone()
                    next_id = 1 if (not res or res['max_id'] is None) else res['max_id'] + 1
                    
                    cursor.execute("""
                        INSERT INTO faculty (faculty_id, name, email, password)
                        VALUES (%s, 'Placement Officer', 'tap@nitandhra.ac.in', 'placementOfficerNITandhra2015')
                    """, (next_id,))
                    
                # Check if tapc@nitandhra.ac.in exists
                cursor.execute("SELECT COUNT(*) as count FROM faculty WHERE email = 'tapc@nitandhra.ac.in'")
                if cursor.fetchone()['count'] == 0:
                    cursor.execute("SELECT MAX(faculty_id) as max_id FROM faculty")
                    res = cursor.fetchone()
                    next_id = 1 if (not res or res['max_id'] is None) else res['max_id'] + 1
                    
                    cursor.execute("""
                        INSERT INTO faculty (faculty_id, name, email, password)
                        VALUES (%s, 'Placement Officer', 'tapc@nitandhra.ac.in', 'placementOfficerNITandhra2015')
                    """, (next_id,))
                    
                conn.commit()
                print(f"Successfully updated faculty in {db_name}")
            else:
                print(f"No faculty table in {db_name}")
                
        cursor.close()
        conn.close()
        print("Update complete.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_faculty()
