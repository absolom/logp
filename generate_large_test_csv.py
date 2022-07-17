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

def generate_data(num_rows, gen, status_increment=100000):
    with open('test.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        headers = gen.header()
        start_time = datetime.datetime.now().timestamp()
        for entry_num in range(0,num_rows):
            row = gen.row()
            writer.writerow(row)
            if entry_num % status_increment == 0:
                if entry_num:
                    curr_elapsed = datetime.datetime.now().timestamp() - start_time
                    rate = entry_num / curr_elapsed
                    est_time = int(((num_rows - entry_num) / rate) / 60)
                    print('{:d} / {:d}, estimated time left {:d}m left'.format(int(entry_num/status_increment), int(num_rows/status_increment), est_time))

if __name__ == '__main__':
    generate_data(10**6 * 40, GeneratorBasic(start_time=100000000))

