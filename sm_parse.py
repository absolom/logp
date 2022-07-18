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

class StateMachine:
    @staticmethod
    def is_start(row):
        if instance_start_re.match(row[instance_start_col]):
            return StateMachine()
        else:
            return None

    def __init__(self):
        self.state = 'open'
        self.transitions = []

    def add_state(self, state):
        self.states[state.name] = state
        self.transitions += state.transitions

states = ['alive']
events = [(0,)]

"""
states : open
events : 
    - column : 'Msg'
      event : 'New command started ctag : 0x([0-9a-fA-F]+)']
        transitions : {None : 'open'}
        values :
            1 : tag
    - 'Command completed ctag : 0x([0-9a-fA-F]+)'
        transitions : {'open' : None}
        values :
            1 : tag



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

