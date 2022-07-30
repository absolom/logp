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

>> Use Cases

- Time how long it takes to run a test, compute average and std deviation.
  - SM with 1 instance max, no tag.
  instances = get_sm_instances(state_machine_name)
  instances = [x for x in instances if x.dead]
  lifetimes = [x.lifetime('Timestamp') for x in instances]
  plt = histogram(lifetimes, bins=15)
  plt.show()

- Plot number of instances of SM that are open vs. time.
  instances = get_sm_instances(state_machine_name)
  event_times  = [x.start().get('Timestamp') for x in instances]
  event_times += [x.end().get('Timestamp') for x in instances]
  xy_data = [(x, sum([1 for y in instances if y.is_open(x)]) for x in event_times]
  plt = scatter(xy_data)
  plt.show()

- Find instances of SM that had an error reported.
  instances = get_sm_instances(state_machine_name)
  err_instances = [x for x in instances if x.field_contains(field_name, field_contents)]
  print([x.start().get('Timestamp') for x in err_instances])

- The distribution of times each tag of a SM is used
  instances = get_sm_instances(state_machine_name)
  tags = [x.get('ctag') for x in instances)
  plt = histogram(tags)
  plt.show()

- Other ideas
  eid = lookup_eid_by_match('Starting REM load')
  events = get_events_by_eid(eid)
  ts_start = get_fields_from_events(events, ['Timestamp'])

  eid = lookup_eid_by_match('Finished REM load')
  events = get_events_by_eid(eid)
  ts_stop = get_fields_from_events(events, ['Timestamp'])

  eid = lookup_eid_by_sm_transition(state_machine_name, start_state, end_state)
  events = get_events_by_eid(eid)
  field_vals = get_fields_from_events(events, [field_name0, field_name1, ...])
    - field_vals is tuple of lists, where each list is a sequence of values that field took for the events


  x := timestamp from state_machine_name:start_state->end_state

  - start_state and end_state may be * for any state, and None for dead.

> Work Log

-Look up how to build a table with specific indexes

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

>> Large file vim

syntax off
filetype off
set noundofile
set noswapfile
set noloadplugins

> SQL Reference

>> Retrieving adjacent lines

select * from (select * from logs_small where Timestamp > 100000246 limit 4) union select * from (select * from logs_small where Timestamp < 100000246 order by Timestamp desc limit 4);



