# Generate a large (6GB) .csv file to test tool

import sys
import csv
import datetime
from random import randint

class GeneratorBasic:
    def __init__(self, max_data=2**32-1, start_time=0):
        self.timestamp = start_time
        self.max_data = max_data
        self.entry_num = 0

    def header(self):
        return ['Timestamp', 'Module', 'Submodule', 'Msg', 'Data1', 'Data2', 'Data3', 'Data4']

    def row(self):
        self.timestamp += randint(8, 125)
        module = 'Mod{:d}'.format(randint(1,6))
        submodule = 'Submod{:d}'.format(randint(1,16))
        msg = 'This is a log entry message for log entry # {:d}'.format(self.entry_num)
        data = ['0x{:08x}'.format(randint(0, self.max_data)) for x in range(0,4)]
        row = [str(self.timestamp), module, submodule, msg, data[0], data[1], data[2], data[3]]

        self.entry_num += 1
        return row

class GenerateStates:
    class Command:
        def __init__(self, tag):
            self.tag = tag

    def __init__(self, gen):
        self.gen = gen
        self.tags_closed = [self.Command(tag=x) for x in range(0,256)]
        self.tags_open = []
        self.enable_lossy = True

    def header(self):
        return self.gen.header()

    def row(self):
        val = randint(1,100)
        row = self.gen.row()
        if val < 2:
            if self.tags_closed:
                cmd = self.tags_closed.pop(randint(0, len(self.tags_closed)-1))
                row[3] = 'New command started ctag : 0x{:02X}'.format(cmd.tag)
                self.tags_open.append(cmd)
        elif val < 4:
            if self.tags_open:
                cmd = self.tags_open.pop(randint(0, len(self.tags_open)-1))
                row[3] = 'Command blocked ctag : 0x{:02X}'.format(cmd.tag)
        elif val < 6:
            if self.tags_open:
                cmd = self.tags_open.pop(randint(0, len(self.tags_open)-1))
                row[3] = 'Command completed ctag : 0x{:02X}'.format(cmd.tag)
                self.tags_closed.append(cmd)

        if randint(1,1000) < 2:
            row = None

        return row

def generate_data(num_rows, gen, filename, status_increment=100000):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        headers = gen.header()
        writer.writerow(headers)
        start_time = datetime.datetime.now().timestamp()
        for entry_num in range(0,num_rows):
            row = gen.row()
            if row is not None:
                writer.writerow(row)
            if entry_num % status_increment == 0:
                if entry_num:
                    curr_elapsed = datetime.datetime.now().timestamp() - start_time
                    rate = entry_num / curr_elapsed
                    est_time = int(((num_rows - entry_num) / rate) / 60)
                    print('{:d} / {:d}, estimated time left {:d}m left'.format(int(entry_num/status_increment), int(num_rows/status_increment), est_time))

if __name__ == '__main__':
    # generate_data(10**6 * 40, GeneratorBasic(start_time=100000000))
    generator = GenerateStates(GeneratorBasic(start_time=100000000))
    generate_data(10**4, generator, 'test_small.csv')
    #generate_data(10**6 * 40, generator, 'test.csv')

