# Prototype statemachine parsing

import sqlite3

con = sqlite3.connect('logs.db')
cur = con.cursor()
for row in cur.execute('pragma table_info(logs)'):
    print(row)
for row in cur.execute('select * from logs limit 100'):
    print(row)
con.close()


prefilter = 'select * from logs where Module == "Mod4"'

