import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='Pallavi@2007')
c = conn.cursor(dictionary=True)
c.execute("SHOW DATABASES LIKE 'placement_portal%'")
dbs = c.fetchall()
for d in dbs:
    db_name = list(d.values())[0]
    b = mysql.connector.connect(host='localhost', user='root', password='Pallavi@2007', database=db_name)
    bc = b.cursor(dictionary=True)
    try:
        bc.execute("SELECT id, job_id, company_name, reminder_date, reminder_sent FROM jobs WHERE reminder_date IS NOT NULL")
        rows = bc.fetchall()
        for r in rows:
            print(db_name, r)
        if not rows:
            print(db_name, "- no reminders set")
    except Exception as e:
        print("Error:", db_name, e)
    b.close()
conn.close()
