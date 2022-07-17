> Overview

State-based log parser.

- Define statemachines that can track entity instances throughout their lifetime.
- Handles lossy logs.
- Visualizations.
- Integration with database implementation for indexing and faster lookups.

> Design

Log data loaded into an SQLite database. SQLite program is used directly for
manual log viewing. Python sqlite3 module is used for interfacing to the
database and running data analysis tools.

> Work Log

>> SQLite

SQLite can be used to load large amounts of log data and provide a fast
interface for querying/filtering that data.

generate a test .csv file with generate_large_test_csv.py, should be about ~4GB
run sqlite and load it:
$ sqlite
sqlite> .mode csv
sqlite> .import test.csv logs
sqlite> .save logs.db

The above takes a minute or so, and loads the csv file into table "logs" then
saves the entire DB to logs.db f
Now this database can be opened:

$ sqlite logs.db
sqlite> select * from logs limit 100;

Additonal csv files can be added to the existing table:
sqlite> .mode csv
sqlite> .import --skip 1 test2.csv logs

skip 1 is needed otherwise the row with header labels will be added to the table

