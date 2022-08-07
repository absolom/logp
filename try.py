import os
import csv
import sys
import subprocess
import re
from util import load_yaml

class BufferedReverseReader():
    def __init__(self, filename):
        self.filename = filename
        self.buffer = ''
        self.buffer_lines = []
        self.file = None
        self.chunk_size = 1024*1024*300

    def __next__(self):

        if not self.buffer_lines:
            size = self.file.tell()

            to_read = min(self.chunk_size, self.file.tell())

            if to_read == 0:
                raise StopIteration()

            self.file.seek(-to_read, 1)

            chunk = self.file.read(self.chunk_size).decode('utf-8')
            newpos = self.file.seek(-to_read, 1)
            if self.buffer:
                chunk += self.buffer
                self.buffer = None
            self.buffer_lines = chunk.split(os.linesep)
            if chunk[0:1] != os.linesep:
                self.buffer = self.buffer_lines[0]
                self.buffer_lines = self.buffer_lines[1:]

        ret = self.buffer_lines.pop()
        return ret

    def __iter__(self):
        return self

    def __enter__(self):
        self.done = False
        self.file = open(self.filename, 'rb')
        self.file.seek(0, 2)
        return self

    def __exit__(self, type, value, traceback):
        self.file.close()

def calculate_segments(f, max_size):
    size_left = f.seek(0,2)
    segments = []
    index = 0
    while True:
        seg_size = min(max_size, size_left)
        if seg_size == max_size:
            offset = 0
            while offset != seg_size:
                f.seek(index+seg_size-offset, 0)
                dat = f.read(1).decode('utf-8')
                if dat == '\n':
                    seg_size -= offset
                    break
                offset += 1
            print(offset)
        if not seg_size:
            break
        segments.append((index, seg_size))
        print(segments)
        index += seg_size
        size_left -= seg_size
    return segments

def split_file(filename, max_size=2147483647):
    # TODO : Split file on line boundary that is less than or equal to max_size
    ret = []
    with open(filename, 'rb') as f:
        segments = calculate_segments(f, max_size)

        chunk_size = 1024*1024*500
        for seg_ind,segment in enumerate(segments):
            offset = segment[0]
            seg_size = segment[1]
            f.seek(offset,0)
            seg_filename = filename + '.seg{:d}'.format(seg_ind)
            ret.append(seg_filename)
            with open(seg_filename, 'bw') as f2:
                chunk_left = seg_size
                while chunk_left:
                    to_read = min(chunk_size, chunk_left)
                    chunk_left -= to_read
                    dat = f.read(to_read)
                    f2.write(dat)
    return ret

def find_event_lines(csv_filename, event_lines={}):
    searches = []
    for ind,event in enumerate(config['events']):
        search = event['match'][0][1]
        try:
            # TODO : Configure ag to not put line number
            subprocess.check_call("ag --nonumbers '{:s}' {:s} > tmp.ag".format(search, csv_filename), shell=True)
        except subprocess.CalledProcessError as e:
            if e.returncode != 1:
                raise e
        with BufferedReverseReader('tmp.ag') as f:
            lines = list(f)
            print("Found {} events".format(len(lines)))
        if ind not in event_lines:
            event_lines[ind] = []
        event_lines[ind] += lines
    return event_lines

def find_all_event_lines(config, csv_filename, sm_name=None):
    searches = []
    for event in config['events']:
        if sm_name and not [x for x in event['transitions'] if x['sm'] == sm_name]:
            continue
        # if [x for x in event['match'] if x[0]]:
        #     raise NotImplemented('No support for column matches yet.')
        matches = event['match']
        if len(matches) == 1:
            searches += [x[1] for x in event['match'] if not x[0]]
        else:
            search = [x[1] for x in event['match']]
            search = '&'.join(search)
            search = '({:s})'.format(search)
            searches += search
    subprocess.check_call("ag '{:s}' {:s} > tmp.ag".format('|'.join(searches), csv_filename), shell=True)
    with BufferedReverseReader('tmp.ag') as f:
        event_lines = list(f)
    return event_lines

class Event:
    def __init__(self, eid, row, fields):
        self.eid = eid
        self.row = row
        self.fields = fields

class Instance:
    def __init__(self):
        self.events = []

def line_to_row(line):
    rdr = csv.reader([line])
    return rdr.__next__()

def parse_event(eid, event_def, line, hind):
    fields = {}
    row = None
    field_defs = event_def['field_defs']
    for field_def in field_defs:
        col = field_def['regex'][0]
        regex = field_def['regex'][1]
        if regex:
            if col:
                if not row:
                    row = line_to_row(line)
                col_val = row[hind[col]]
            else:
                col_val = line
            mo = re.search(regex, col_val)
            extracted_fields = [mo.group(x+1) for x in range(0,len(mo.groups()))]
        else:
            if not row:
                row = line_to_row(line)
            col_val = row[hind[col]]
            extracted_fields = [col_val]

        for ind,label in enumerate(field_def['labels']):
            name = label['name']
            parse = label['parse']
            val = extracted_fields[ind]
            if parse:
                exec('parser = {:s}\nfields[name] = parser(val)'.format(parse))
            else:
                fields[name] = val

    return Event(eid, line, fields)

def find_sm_instances(config, sm_name, event_lines, hind):

    # Create event instances
    event_defs = config['events']
    matches = [x['match'][0][1] for x in event_defs]
    events = []
    for line in event_lines:
        if not line:
            continue
        eid = [ind for ind,x in enumerate(matches) if x in line][0]
        event = parse_event(eid, event_defs[eid], line, hind)
        events.append(event)

    # Create SM instances
    instances = []
    open_instances = {}
    for event in events:
        eid = event.eid
        event_def = event_defs[eid]
        for transition in event_def['transitions']:
            sm = transition['sm']
            if sm == sm_name:
                tag = event.fields['ctag']
                from_state = transition['from']
                #to_state = transition['to']

                if tag not in open_instances:
                    instance = Instance()
                    open_instances[tag] = instance
                    instances.append(instance)

                instance = open_instances[tag]
                instance.events.insert(0, event)

                if from_state is None:
                    del open_instances[tag]

    return instances

# def run2(csv_filename):
#     searches = []
#     for event in config['events']:
#         searches += [x[1] for x in event['match'] if not x[0]]
#     subprocess.check_call("ag '{:s}' {:s} > tmp.ag".format('|'.join(searches), csv_filename), shell=True)
#     with BufferedReverseReader('tmp.ag') as f:
#         lines = list(f)
#         print("Found {} events".format(len(lines)))

# def run3(csv_filename):
#     matches = []
#     with BufferedReverseReader(csv_filename) as f:
#         rdr = csv.reader(f)
#         for line in rdr:
#             if not line:
#                 continue
#             for event in config['events']:
#                 for mtch in event['match']:
#                     col = mtch[0]
#                     key = mtch[1]
#                     entry = line[hind[col]]
#                     if key in entry:
#                         matches.append(line)

config = load_yaml('config2.yaml')
#csv_filename = 'test_small.csv'
csv_filename = 'log.csv'
#csv_filename = 'test_med.csv'
#csv_filename = 'test_med_med.csv'

#files = split_file(csv_filename)
files = ['log.csv.seg0', 'log.csv.seg1', 'log.csv.seg2']

with open(files[0], 'r', newline='') as f:
    rdr = csv.reader(f)
    header_row = rdr.__next__()

hind = {}
for ind,header in enumerate(header_row):
    hind[header] = ind

files.reverse()

#import cProfile
for file in files:
    event_lines = {}

    #lines = find_all_event_lines(config, file, sm_name='ctag')
    lines = find_all_event_lines(config, file)
    instances = find_sm_instances(config, 'ctag', lines, hind)

    lines = find_all_event_lines(config, file, sm_name='subtag')
    instances = find_sm_instances(config, 'subtag', lines, hind)

    print(f'found {len(instances)} instances!')

"""
-parse X more lines
-parse until X is true
-save parsing state to file so it can be resumed later
*add support for silver surfer
-add support for multiprocessing
-handle lossy logs
-add support for relative events
"""

