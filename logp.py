
import yaml
import sqlite3
import re
import pprint
import sys
import argparse
import csv
import os
import subprocess
import tty
import termios

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

    headers = get_headers(cur, 'log')
    hind = { headers[x] : x for x in range(0,len(headers)) }

    # TODO : Faster to do a select for each match string or combined search?

    state_machine_events = { 'subtag' : [], 'sm' : [] }

    rows = cur.execute('select * from log where {:s};'.format(sql_match))
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
    #print(cnt)

    return events

def create_table(cur, table_def):
    # Create table
    name = table_def['name']
    cmd = 'create table {:s} ('.format(name)
    cols = table_def['columns']
    for ind in range(0,len(cols)):
        label = cols[ind]['label']
        typ = cols[ind]['type']
        cmd += '{:s} {:s}'.format(label,typ)
        if label in table_def['primary_key']:
            cmd += ' not null'
        cmd += ','
    cmd += 'primary key ({:s})'.format(','.join(table_def['primary_key']))
    cmd += ');'
    cur.execute(cmd)
    print('Table created with : {:s}'.format(cmd))

    # Create indexes
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

    return parser.parse_args()

gReplCmds = set()
gCmds = []

def replcmd(func):
    gReplCmds.add(func)
    name = func.__name__[4:]
    tokens = name.split('_')
    for lvl,token in enumerate(tokens):
        if len(gCmds) <= lvl:
            gCmds.append(set())
        gCmds[lvl].add(token)
    return func

@replcmd
def cmd_db_init(con, database):
    """doc help string"""
    if os.path.isfile(database):
        con.close()
        os.remove(database)
        con = sqlite3.connect(database)
        cur = con.cursor()
    table_def = [x for x in config['tables'] if x['name'] == 'log'][0]
    create_table(cur, table_def)
    create_table(cur, table_def_events)
    return 'db init success'

@replcmd
def cmd_help():
    """Prints this help"""
    cmds = list(gReplCmds)
    cmds = [(x.__name__[4:].replace('_',' '),x.__doc__) for x in cmds]
    cmds.sort()
    ret = ''
    for name,doc in cmds:
        ret += f'\n{name} - {doc}'
    return ret

def match_cmd(cmd, subcmd):
    def match_by_unique_prefix(cmd,cmds):
        ret = None
        if cmd:
            for ind in range(1,len(cmd)+1):
                substr = cmd[0:ind]
                matches = [x for x in cmds if re.match(r'^{:s}'.format(substr), x) and len(cmd) <= len(x)]
                if len(matches) == 1:
                    ret = matches[0]
        return ret
    rcmd = match_by_unique_prefix(cmd,gCmds[0])
    rsubcmd = match_by_unique_prefix(subcmd,gCmds[1])
    return (rcmd,rsubcmd)

@replcmd
def cmd_quit():
    """Exits"""
    pass

def process_cmd(args, con, database):
    cmd = args[0]
    subcmd = None
    if len(args) > 1:
        subcmd = args[1]
    (cmd,subcmd) = match_cmd(cmd, subcmd)

    ret = None
    done = False
    if cmd == 'db' and subcmd == 'init':
        ret = cmd_db_init(con, database)
    elif cmd == 'help':
        ret = cmd_help()
    elif cmd == 'quit':
        done = True

    return (ret,done)

def enter_repl(args, con, prompt='> '):
    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def should_echo(ch):
        if ch == '\r': # TODO : Why we get \r instead of \n in WSL?
            return '\n'
        else:
            return None

    def should_continue(ch):
        return False

    def should_break(ch):
        if ch == '\r':
            return True
        else:
            return False

    def parse_ctrlcode(code):
        if code == '\x1b[A':
            return 'UP_ARROW'
        elif code == '\x1b[B':
            return 'DOWN_ARROW'
        elif code == '\x1b[C':
            return 'LEFT_ARROW'
        elif code == '\x1b[D':
            return 'RIGHT_ARROW'
        else:
            return None

    while True:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = ''
        ctrlcode = None
        while True:
            ch = getch()
            if ctrlcode:
                #breakpoint()
                ctrlcode += ch
                if ch != '[':
                    term_cmd = parse_ctrlcode(ctrlcode)
                    if term_cmd == 'UP_ARROW':
                        sys.stdout.write('Not implemented : UP_ARROW\n')
                    elif term_cmd == 'DOWN_ARROW':
                        sys.stdout.write('Not implemented : DOWN_ARROW\n')
                    elif term_cmd == 'RIGHT_ARROW':
                        sys.stdout.write('Not implemented : RIGHT_ARROW\n')
                    elif term_cmd == 'LEFT_ARROW':
                        sys.stdout.write('Not implemented : LEFT_ARROW\n')
                    ctrlcode = None
                    break
                continue
            else:
                if ch == '\x1b':
                    ctrlcode = ch
                    continue
                echo_ch = should_echo(ch)
                if echo_ch is not None:
                    sys.stdout.write(echo_ch)
                if should_continue(ch):
                    continue
                if should_break(ch):
                    break

            line += ch
            sys.stdout.write(ch)
            sys.stdout.flush()
        if not line.strip():
            continue
        (outp,done) = process_cmd(line.split(' '), con, args.database)
        if done:
            return
        if outp is None:
            outp = 'Command not recognized...'
        sys.stdout.write(f'{outp}\n\n')

def enter_repl_old(args, con, prompt='> '):
    while True:
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = sys.stdin.readline().strip()
        if not line:
            continue
        (outp,done) = process_cmd(line.split(' '), con, args.database)
        if done:
            return
        if outp is None:
            outp = 'Command not recognized...'
        sys.stdout.write(f'{outp}\n\n')

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

if __name__ == '__main__':
    args = parse_args()

    config = load_yaml(args.config)
    con = sqlite3.connect(args.database)
    cur = con.cursor()

    if args.cmd == 'repl':
        enter_repl(args, con, prompt='logp> ')
    elif args.cmd == 'db' and args.subcmd == 'init':
        if os.path.isfile(args.database):
            con.close()
            os.remove(args.database)
            con = sqlite3.connect(args.database)
            cur = con.cursor()
        table_def = [x for x in config['tables'] if x['name'] == 'log'][0]
        create_table(cur, table_def)
        create_table(cur, table_def_events)
    elif args.cmd == 'db' and args.subcmd == 'import':
        con.close()
        import_csv(args.database, 'log', args.csv_file)
    elif args.cmd == 'parse' and args.subcmd == 'events':
        event_defs = config['events']
        events = parse_events(event_defs, cur)
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
