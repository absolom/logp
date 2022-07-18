# Prototype statemachine parsing

import sqlite3

#con = sqlite3.connect('logs.db')
#cur = con.cursor()
#for row in cur.execute('pragma table_info(logs)'):
#    print(row)
#for row in cur.execute('select * from logs limit 100'):
#    print(row)
#con.close()

# TODO : Lossy log
# TODO : Multiple state state machine (other than open/closed)
# TODO : Multi-entry state events

#prefilter = 'select * from logs where Module == "Mod4"'
prefilter = 'select * from logs'

"""
SM definitions

Need to define the log event which spawns the SM instance.

Each state needs to define which states it can transition to and what log
events trigger those transitions.

Each state needs to define when the SM instance is destroyed.

SM instance needs to store references to all relevant log entries as well as
data scraped from those entries.

state_closed = 
state_entry = ''
state_exit = ''

"""

import re

instance_start_col = 3
instance_start_re = re.compile(r'New command started ctag : 0x([0-9a-fA-F]+)')

class RegexParser:
    def __init__(self, pattern, labels):
        self.pattern = r'ctag : 0x([0-9a-fA-F]+)'
        self.labels = labels

    def parse(self, line):
        mo = re.search(self.pattern, line)
        if mo:
            groups = [mo.group(x) for x in range(1,len(self.labels))]
            return {x:y for x,y in zip(self.labels, groups)}
        else:
            raise ValueError("Couldn't parse field.")

class Field:
    def __init__(self, col, val, offset=0):
        self.offset = offset
        self.col = col
        self.val = val

class Event:
    def __init__(self, trigger, fields=[]):
        self.trigger = trigger
        self.fields = fields

# TODO : Figure out how to parse values from fields; pair up Field instances with Parser instances?

class StateClosed:
    def __init__(self):
        self.name = 'closed'
        self.transitions = { Event(Field('Msg', 'New command started ctag')) : None }
        self.triggers = [x.trigger for x in self.transitions]

class StateOpen:
    def __init__(self):
        self.name = 'open'
        self.transitions = { Event(Field('Msg', 'Command completed ctag')) : None }
        self.triggers = [x.trigger for x in self.transitions]

class StateMachine:
    @staticmethod
    def is_start(row):
        if instance_start_re.match(row[instance_start_col]):
            return StateMachine()
        else:
            return None

    def __init__(self):
        self.states = None
        self.

states = ['alive']
events = [(0,)]

"""
states:
    - event:
        column: Msg
        str: "New command started ctag"
      values:
        - offset: 0
          column: Msg
          regex: "ctag : 0x([0-9a-fA-F]+)"
          labels: [tag]
      transitions: { None: open }
    - event:
        column: Msg
        str: "Command completed ctag"
      values:
        - offset: 0
          column: Msg
          regex: "ctag : 0x([0-9a-fA-F]+)"
          labels: [tag]
      transitions: { open: None }
"""

class State:
    def __init__(self, name):
        self.name = name
        self.transitions = []

def rematch(expr, item):
    return re.match(expr, item) is not None

#con.create_function('REGEXP', 2, rematch)
#for row in cur.execute("select * from logs where Msg like 'New command started ctag%'"):

start = State('start')
start.transitions = 

con = sqlite3.connect('logs_small.db')
cur = con.cursor()
for row in cur.execute('pragma table_info(logs_small)'):
    print(row)
cur = con.cursor()
for row in cur.execute("select * from logs_small where instr(Msg, 'New command') > 0;"):
    print(row)
con.close()

