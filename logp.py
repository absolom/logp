
import yaml
import sqlite3
import pprint
import sys
import argparse
import csv
import os
import subprocess
import re
from util import load_yaml
submodule_imports = ['repl']

from pathlib import Path
script_dir = Path(__file__).parent.absolute()
for dep in submodule_imports:
    sys.path.append(str(script_dir) + f'/{dep}')
    exec(f'import {dep}')

class Event:
    def __init__(self, eid):
        self.eid = eid
        self.fields = {}
        self.tags = None

    def __str__(self):
        pp = pprint.PrettyPrinter(indent=2)
        ret = 'Event Id : {:d} - {:s}'.format(self.eid, pp.pformat(self.fields))
        return ret

    def add_tag(self, tag):
        if not self.tags:
            self.tags = []
        self.tags.append(tag)

class SmInstance:
    def __init__(self, tag):
        self.tag = tag
        self.events = []

    def add_event(self, event):
        self.events.append(event)


def get_headers(cur, table_name):
    headers = []
    rows = cur.execute('pragma table_info({:s});'.format(table_name))
    for row in rows:
        headers.append(row[1])
    return headers

def find_sm_open_events(sm_name, events):
    open_eids = []
    for eid,event in enumerate(events):
        for transition in event['transitions']:
            if transition['sm'] == sm_name and transition['from'] == 'None':
                open_eids.append(eid)
    return open_eids

def find_sm_close_events(sm_name, events):
    close_eids = []
    for eid,event in enumerate(events):
        for transition in event['transitions']:
            if transition['sm'] == sm_name and transition['to'] == 'None':
                close_eids.append(eid)
    return close_eids

def find_sm_events(sm_name, event_defs):
    sm_eids = []
    for ind,edef in enumerate(event_defs):
        if [x['sm'] for x in edef['transitions'] if x['sm'] == sm_name]:
            sm_eids.append(ind)
    return sm_eids

def query_event_table(eids, cur):
    cmd = 'select * from event where Eid == '
    cmd += ' or Eid == '.join([str(x) for x in eids])
    return cur.execute(cmd)

def get_sm_instances(sm_name, config, cur):
    headers = get_headers(cur, 'log')
    hind = { headers[x] : x for x in range(0,len(headers)) }

    event_defs = config['events']
    sm_events = find_sm_events(sm_name, event_defs)
    rows = query_event_table(sm_events, cur)

    eid_open = find_sm_open_events('ctag', config['events'])
    eid_close = find_sm_close_events('ctag', config['events'])
    print(eid_open)
    print(eid_close)

    instances = []
    open_instances = {}
    for row in rows:
        eid = row[1]
        # TODO : Grab the entry from the log table here and pass it to parse_event
        # Probably need a second cursor
        # TODO : Abstract the data source, don't write code dependent on
        # cursor/connection, just dep on the data source
        event = parse_event(eid, event_defs, row, hind)
        tag = event.get_tag()

        if eid in eid_open:
            sm = SmInstance(tag)
            open_instances[tag] = sm
            instances.append(sm)
        else:
            sm = open_instances[tag]

        if eid in eid_close:
            open_instances[tag] = None

        sm.add_event(event)

    print(len(instances))

def parse_event(eid, event_defs, row, hind):
    event = Event(eid)
    #events.append(event)
    event_def = event_defs[eid]
    for field_def in event_def['field_defs']:
        col = field_def['regex'][0]
        regex = field_def['regex'][1]
        breakpoint()
        val = row[hind[col]]
        if regex:
            mo = re.search(regex, val)
            if not mo:
                raise RuntimeError('Match not found where expected')
            for ind,label in enumerate(field_def['labels']):
                name = label['name']
                parse_code = 'parser = {:s}\n'.format(label['parse'])
                parse_code += 'event.fields[name] = parser(mo.group(ind+1))'
                exec(parse_code)
        else:
            for ind,label in enumerate(field_def['labels']):
                name = label['name']
                event.fields[name] = val
    return event

class DataSourceCsv:

    def __init__(self, filename):
        self.filename = filename
        with open(self.filename, newline='') as f:
            rdr = csv.reader(f)
            self.headers = rdr.__next__()
            self.hind = {}
            for ind,col in enumerate(self.headers):
                self.hind[col] = ind
        self.events = None

    def get_rows_from_match(self, match_strings):
        ret = []
        with open(self.filename, newline='') as f:
            rdr = csv.reader(f)
            rdr.__next__() # skip header
            for row in rdr:
                for col,key in match_strings:
                    if key in row[self.hind[col]]:
                        ret.append(row)
        return ret


    def get_headers(self):
        return self.headers

    def save_events(self, events):
        self.events = events

class DataSourceSqlite:

    def __init__(self, con):
        self.con = con
        self.cur = con.cursor()

    def get_rows_from_match(self, match_strings):
        """match_strings is list of (column_name,search_string)"""
        sql_match = ["instr({:s},'{:s}') != 0".format(x[0], x[1]) for x in match_strings]
        sql_match = ' or '.join(sql_match)
        rows = self.cur.execute('select * from log where {:s};'.format(sql_match))
        return rows

    def get_headers(self):
        table_name = 'log'
        headers = []
        rows = self.cur.execute('pragma table_info({:s});'.format(table_name))
        for row in rows:
            headers.append(row[1])
        return headers

    def save_events(self, events):
        rows = [(x.fields['timestamp'], x.eid) for x in events]
        insert_rows(self.cur, 'event', rows)

def parse_events(event_defs, data):
    match_strings = [x['match'] for x in event_defs]

    headers = data.get_headers()
    hind = { headers[x] : x for x in range(0,len(headers)) }

    state_machine_events = { 'subtag' : [], 'sm' : [] }

    rows = data.get_rows_from_match(match_strings)

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
            if 'tag' in event_def:
                for tag in event_def['tag']:
                    event.add_tag(tag)
            for field_def in event_def['field_defs']:
                col = field_def['regex'][0]
                regex = field_def['regex'][1]
                val = row[hind[col]]
                if regex:
                    mo = re.search(regex, val)
                    if not mo:
                        raise RuntimeError('Match not found where expected')
                    for ind,label in enumerate(field_def['labels']):
                        name = label['name']
                        parse_code = 'parser = {:s}\n'.format(label['parse'])
                        parse_code += 'event.fields[name] = parser(mo.group(ind+1))'
                        exec(parse_code)
                else:
                    for ind,label in enumerate(field_def['labels']):
                        name = label['name']
                        event.fields[name] = val
    sys.stdout.write('\n')

    return events

def create_table(cur, table_def, noindex=False, nokey=False):
    # Create table
    name = table_def['name']
    cmd = 'create table {:s} ('.format(name)
    cols = table_def['columns']
    for ind in range(0,len(cols)):
        label = cols[ind]['label']
        typ = cols[ind]['type']
        if ind:
            cmd += ','
        cmd += '{:s} {:s}'.format(label,typ)
        if not nokey:
            if label in table_def['primary_key']:
                cmd += ' not null'
    if not nokey:
        cmd += ',primary key ({:s})'.format(','.join(table_def['primary_key']))
    cmd += ');'
    cur.execute(cmd)
    print('Table created with : {:s}'.format(cmd))

    # Create indexes
    if not noindex:
        create_table_indexes(cur, table_def)

def create_table_indexes(cur, table_def):
    name = table_def['name']
    for ind,index in enumerate(table_def['indexes']):
        sql_cols = ','.join(index)
        cmd = 'create index ind{:d}_{:s} on {:s} ({:s});'.format(ind,name,name,sql_cols)
        cur.execute(cmd)
        print('Index created with : {:s}'.format(cmd))

def insert_rows(cur, table, rows):
    cur.execute('begin transaction;')
    for row in rows:
        row = ["'{}'".format(x) for x in row]
        entry = ','.join(row)
        cmd = 'insert into {:s} (Timestamp,Eid) values ({:s});'.format(table, entry)
        cur.execute(cmd)
    cur.execute('commit;')

def import_csv(db_filename, table, csv_filename):
    cmd = '.import --csv --skip 1 {:s} {:s}'.format(csv_filename, table)
    subprocess.check_call('sqlite3 {:s} "{:s}"'.format(db_filename, cmd), shell=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Log analysis utility.')
    parser.add_argument('--config', default='config.yaml', help='YAML file with definitions for logs (default config.yaml).')
    parser.add_argument('--database', default='log.db', help='Sqlite3 database filename (default log.db).')
    parser.add_argument('--csv', default='log.csv', help='Log data (default log.csv).')
    subparsers = parser.add_subparsers(dest='cmd', required=True, help='')

    parser_db = subparsers.add_parser('db', help='Sqlite3 database creation and manipulation.')
    subparsers_db = parser_db.add_subparsers(dest='subcmd', required=True, help='')
    parser_db_create = subparsers_db.add_parser('init', help='Initializes tables.')
    parser_db_import = subparsers_db.add_parser('import', help='Populate DB from csv file.')
    parser_db_import.add_argument('csv_file', help='File to import data from.')

    parser_parse = subparsers.add_parser('parse', help='Parse data out of the logs.')
    subparsers_parse = parser_parse.add_subparsers(dest='subcmd', required=True, help='')
    parser_parse_events = subparsers_parse.add_parser('events', help='Parse all events.')
    # parser_parse_events.add_argument('--nosave', help='Generate events but do not 

    parser_repl = subparsers.add_parser('repl', help='Enter the CLI.')

    parser_script = subparsers.add_parser('script', help='Run the specified script.')
    parser_script.add_argument('filename', help='Filename of the script.')

    return parser.parse_args()

@repl.replcmd()
def cmd_db_import(cargs, args, data_db, data_csv):
    """Imports from supplied csv file."""
    if len(cargs) != 1:
        return None
    import datetime
    ts = datetime.datetime.now().timestamp()
    import_csv(args.database, 'log', cargs[0])
    ret = 'Total time {:f}m'.format((datetime.datetime.now().timestamp() - ts) / 60.0)
    # con = sqlite3.connect(args.database)
    # cur = con.cursor()
    # config = load_yaml(args.config)
    # table_def = [x for x in config['tables'] if x['name'] == 'log'][0]
    # create_table(cur, table_def, noindex=True, nokey=True)
    return ret

@repl.replcmd()
def cmd_db_init(cargs, args, data_db, data_csv):
    """Initializes the database (wipes any existing data) and creates new empty tables."""
    if os.path.isfile(args.database):
        os.remove(args.database)
    con = sqlite3.connect(args.database)
    cur = con.cursor()
    table_def = [x for x in config['tables'] if x['name'] == 'log'][0]
    create_table(cur, table_def, noindex=True, nokey=True)
    create_table(cur, table_def_events)
    return 'db init success'

@repl.replcmd()
def cmd_report_events(cargs, args, data_db, data_csv):
    """Reports on what events were found."""
    pass

@repl.replcmd()
def cmd_set_mode(cargs, args, data_db, data_csv):
    """Sets the mode, either csv or db."""
    if len(cargs) != 1:
        return None
    if cargs[0] not in ['db', 'csv']:
        return None
    global gMode
    gMode = cargs[0]

@repl.replcmd()
def cmd_parse_events(cargs, args, data_db, data_csv):
    """Parses all (or selected) events from the config into their own table for faster queries."""
    import datetime
    ts = datetime.datetime.now().timestamp()
    event_defs = config['events']
    events = parse_events(event_defs, data_db)
    data_db.save_events(events)
    ret = 'Total time {:f}m\nFound {:d} events in DB'.format((datetime.datetime.now().timestamp() - ts) / 60.0, len(events))
    return ret

@repl.replcmd()
def cmd_parse_eventscsv(cargs, args, data_db, data_csv):
    """Parses all (or selected) events from the config into their own table for faster queries."""
    if len(cargs) != 1:
        return None
    import datetime
    ts = datetime.datetime.now().timestamp()
    event_defs = config['events']
    events = parse_events(event_defs, data_csv)
    data_csv.save_events(events)
    ret = 'Total time {:f}m\nFound {:d} events in CSV'.format((datetime.datetime.now().timestamp() - ts) / 60.0, len(events))
    return ret

@repl.replcmd()
def cmd_help(cargs, args, data_db, data_csv):
    """Prints this help."""
    ret = repl.get_help()
    return ret

@repl.replcmd(quitter=True)
def cmd_quit(cargs, args, data_db, data_csv):
    """Exits."""
    return ''

table_def_events = {
    'name' : 'event',
    'columns' : [
        {
            'label' : 'Timestamp',
            'type' : 'int'
        },
        {
            'label' : 'Eid',
            'type' : 'int'
        }
    ],
    'primary_key' : ['Timestamp'],
    'indexes' : [['Eid']]
}

def run_test_script(config, data_db, data_csv):
    event_defs = config['events']
    events = parse_events(event_defs, data_csv)

    bytag = {}
    for event in events:
        if event.tags:
            for tag in event.tags:
                if tag not in bytag:
                    bytag[tag] = []
                bytag[tag].append(event)

    for tag in bytag:
        print(f'{tag} : {len(bytag[tag])}')
    print(len(events))

if __name__ == '__main__':
    args = parse_args()

    config = load_yaml(args.config)
    con = sqlite3.connect(args.database)
    cur = con.cursor()

    data_db = DataSourceSqlite(sqlite3.connect(args.database))
    data_csv = DataSourceCsv(args.csv)

    if args.cmd == 'repl':
        con.close()
        repl.enter_repl(args, data_db, data_csv, prompt='logp> ')
    elif args.cmd == 'script':
        # args.filename
        run_test_script(config, data_db, data_csv)
    elif args.cmd == 'db' and args.subcmd == 'init':
        if os.path.isfile(args.database):
            con.close()
            os.remove(args.database)
            con = sqlite3.connect(args.database)
            cur = con.cursor()
        table_def = [x for x in config['tables'] if x['name'] == 'log'][0]
        create_table(cur, table_def)
        create_table(cur, table_def_events, noindex=True)
    elif args.cmd == 'db' and args.subcmd == 'import':
        con.close()
        import_csv(args.database, 'log', args.csv_file)
    elif args.cmd == 'parse' and args.subcmd == 'events':
        event_defs = config['events']
        events = parse_events(event_defs, data)
        rows = [(x.fields['timestamp'],x.eid) for x in events]
        insert_rows(cur, 'event', rows)

"""
TODO

-After finding all of the state transitions, how should these be stored?
  - Events get stored in a table that links timestamps (primary key of log
    table) to event types.
    - Should event id be added as a colum to the main table?
  - Another table could be added for state transitions, again linking
    events/timestamps to sm type and transition.
  -Would the above tables allow fast generation of SM instance data?

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

-How can event fields be stored in the database?
  - Have a table for each event type? Seems like it would be neccesary as the
    number and type of fields vary by event

- Log parsing will be done on demand instead of all or nothing

-Add support for parsing fields via a struct name (whose definition is pulled
from dwarf data)

-Add concept of "views" which are filtered version of the whole log but
processing steps can be applied to these instead of the whole log to reduce
computation when whole log is not needed
  - Maybe not something so over engineered, instead allow a function to
    provided to get the next row to consider (ie a selector?)?
"""
