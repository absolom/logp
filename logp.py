
import yaml
import sqlite3
import re
import pprint
import sys
import argparse

class Event:
    def __init__(self, eid):
        self.eid = eid
        self.fields = {}

    def __str__(self):
        pp = pprint.PrettyPrinter(indent=2)
        ret = 'Event Id : {:d} - {:s}'.format(self.eid, pp.pformat(self.fields))
        return ret

def load_yaml(filename):
    with open(filename, 'r') as f:
        data = f.read()

    return yaml.safe_load(data)

def get_headers(cur, table_name):
    headers = []
    rows = cur.execute('pragma table_info({:s});'.format(table_name))
    for row in rows:
        headers.append(row[1])
    return headers

def parse_events(event_defs, cur):
    match_strings = [x['match'] for x in event_defs]

    sql_match = ["instr({:s},'{:s}') != 0".format(x[0],x[1]) for x in match_strings]
    sql_match = ' or '.join(sql_match)

    headers = get_headers(cur, 'logs')
    hind = { headers[x] : x for x in range(0,len(headers)) }

    # TODO : Faster to do a select for each match string or combined search?

    state_machine_events = { 'subtag' : [], 'sm' : [] }

    rows = cur.execute('select * from logs where {:s};'.format(sql_match))
    events = []
    cnt = 0
    for row in rows:
        if cnt % 1000 == 0:
            sys.stdout.write('.')
            sys.stdout.flush()
        cnt += 1
        msg = row[hind['Msg']]
        event_ids = [ ind for ind,x in enumerate(match_strings) if match_strings[ind][1] in row[hind[match_strings[ind][0]]] ]
        for eid in event_ids:
            event = Event(eid)
            events.append(event)
            event_def = event_defs[eid]
            for field_def in event_def['field_defs']:
                col = field_def['regex'][0]
                regex = field_def['regex'][1]
                val = row[hind[col]]
                mo = re.search(regex, val)
                if not mo:
                    raise RuntimeError('Match not found where expected')
                for ind,label in enumerate(field_def['labels']):
                    name = label['name']
                    parse_code = 'parser = {:s}\n'.format(label['parse'])
                    parse_code += 'event.fields[name] = parser(mo.group(ind+1))'
                    exec(parse_code)
    sys.stdout.write('\n')
    print(cnt)

    return events

def create_table(cur, table_def):
    # Create table
    name = table_def['name']
    cmd = 'create table {:s} ('.format(name)
    for label,typ in table_def['columns']:
        cmd += '{:s} {:s}'.format(label,typ)
        if col in table_def['primary_key']:
            cmd += ' not null'
        cmd += ','
    cmd += 'primary key ({:s})'.format(','.join(table_def['primary_key']))
    cmd += ');'
    cur.execute(cmd)

    # Create indexes
    for index in table_def['indexes']:
        sql_cols = ','.join(index)
        cmd = 'create index ind{:d}_{:s} on {:s} ({:s});'.format(ind,name,name,sql_cols)
        cur.execute(cmd)

def insert_rows(cur, table, rows):
    cur.execute('begin transaction;')
    for row in rows:
        cmd = 'insert into {:s} table values {:s};'
        cur.execute(cmd)
    cur.execute('commit;')

def parse_args():
    parser = argparse.ArgumentParser(description='Log analysis utility.')
    parser.add_argument('--config', default='config.yaml', help='YAML file with definitions for logs (default config.yaml).')
    subparsers = parser.add_subparsers(dest='cmd', required=True, help='')

    parser_db = subparsers.add_parser('db', help='Sqlite3 database creation and manipulation.')
    subparsers_db = parser_db.add_subparsers(dest='subcmd', required=True, help='')
    parser_db_create = subparsers_db.add_parser('create', help='Create empty database.')
    parser_db_import = subparsers_db.add_parser('import', help='Populate DB from csv file.')
    parser_db_import.add_argument('csv_file', help='File to import data from.')

    parser_parse = subparsers.add_parser('parse', help='Parse data out of the logs.')
    subparsers_parse = parser_parse.add_subparsers(dest='subcmd', required=True, help='')
    parser_parse_events = subparsers_parse.add_parser('events', help='Parse all events.')
    #parser_parse_events.add_argument('--nosave', help='Generate events but do not 

    # parser_db_import = subparsers_db.add_parser('import', help='Populate DB from csv file.')
    # parser_db_import.add_argument('csv_file', help='File to import data from.')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    if args.cmd == 'parse' and args.subcmd == 'events':
        event_defs = load_yaml(args.config)['events']
        con = sqlite3.connect('logs.db')
        cur = con.cursor()
        events = parse_events(event_defs, cur)

    print(events[0])

"""
TODO
- Figure out stages of processing.
  - Process events (specific eid's or events tied to a specific SM, a logical
    set of eid's can be defined and referenced by a label e.g. BE_Errors)
    - Provides list of events with parsed fields
    -Should results be stored in DB table (or at least the option to?)?
    -Handle lossy compound events here
  - Process instances
    - Will group all events related to SM instance's life together
    - Will produce a state transition sequence for the life of the instance.
      Each event in the sequence will have all parsed fields.
    -Handle lossy events here (generate implicit transitions for missing events)
  - Generate visualizations
    - Histograms, etc.

- Log parsing will be done on demand instead of all or nothing

-Add support for parsing fields via a struct name (whose definition is pulled
from dwarf data)

-Add concept of "views" which are filtered version of the whole log but
processing steps can be applied to these instead of the whole log to reduce
computation when whole log is not needed
  - Maybe not something so over engineered, instead allow a function to
    provided to get the next row to consider (ie a selector?)?
"""
