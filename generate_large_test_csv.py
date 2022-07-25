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

class GenerateStatesFromYaml:
    def __init__(self, yaml_data, gen):
        self.yaml = yaml_data
        self.gen = gen

    def header(self):
        return self.gen.header()

    def row(self):
        # TODO : Use data from states.yaml to generate csv log
        val = randint(1,100)
        if val < 2:
            rows = self.transition(randint(0, len(self.tags)-1))
        else:
            rows = [self.gen.row()]

        if self.enable_lossy and randint(1,1000) < 2:
            rows = [x for x in rows if randint(1,1000) > 1]

        return rows

class GenerateStates:
    def __init__(self, gen):
        self.gen = gen
        self.tags = {x : None for x in range(0,256)}
        self.enable_lossy = True

    def transition(self, tag):
        state = self.tags[tag]
        rows = []
        if state is None:
            row = self.gen.row()
            rows.append(row)
            row[3] = 'New command started ctag : 0x{:02X}'.format(tag)
            self.tags[tag] = 'open'
        elif state == 'open':
            row = self.gen.row()
            rows.append(row)
            row[3] = 'Command started processing ctag : 0x{:02X}'.format(tag)
            self.tags[tag] = 'processing'
        elif state == 'processing':
            if randint(0,1) == 0:
                row = self.gen.row()
                rows.append(row)
                row[3] = 'Cache hit, early return ctag : 0x{:02X}'.format(tag)
                self.tags[tag] = 'complete'
            else:
                row = self.gen.row()
                rows.append(row)
                subtag = randint(0,255)
                row[3] = 'Dispatched command ctag : 0x{:02X} subtag : 0x{:02X}'.format(tag,subtag)
                self.tags[tag] = 'dispatch'
        elif state == 'dispatch':
            row = self.gen.row()
            rows.append(row)
            row[3] = 'Command complete ctag : 0x{:02X}'.format(tag)
            self.tags[tag] = 'response'
        elif state == 'response':
            row = self.gen.row()
            row[3] = 'Command response received ctag : 0x{:02X}'.format(tag)
            rows.append(row)
            row = self.gen.row()
            row[3] = 'Response status : {:d}'.format(randint(0,9))
            rows.append(row)
            self.tags[tag] = 'complete'
        elif state == 'complete':
            row = self.gen.row()
            rows.append(row)
            row[3] = 'Command complete ctag : 0x{:02X}'.format(tag)
            self.tags[tag] = None

        return rows

    def header(self):
        return self.gen.header()

    def row(self):
        val = randint(1,100)
        if val < 2:
            rows = self.transition(randint(0, len(self.tags)-1))
        else:
            rows = [self.gen.row()]

        if self.enable_lossy and randint(1,1000) < 2:
            rows = [x for x in rows if randint(1,1000) > 1]

        return rows

def generate_data(num_rows, gen, filename, status_increment=100000):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        headers = gen.header()
        writer.writerow(headers)
        start_time = datetime.datetime.now().timestamp()
        for entry_num in range(0,num_rows):
            rows = gen.row()
            for row in rows:
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



