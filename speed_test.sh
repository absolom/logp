#! /bin/bash

#time ag 'ctag' test_small.csv > tmp.txt
#time ag 'New|omplete' test.csv > tmp.txt
#tail tmp.txt
#time sqlite3 logs_small.db "select * from logs_small where instr(Msg,'ctag') > 0;" > tmp.txt
#time sqlite3 logs.db "explain query plan select * from logs indexed by index0 where instr(Msg,'New') != 0 or instr(Msg,'omplete') != 0;" > tmp.txt
#time sqlite3 logs.db "select * from logs indexed by index0 where instr(Msg,'ctag') != 0;"
#sqlite3 logs.db "select * from logs indexed by index0 where instr(Msg,'ctag') != 0;" &> /dev/null
sqlite3 logs.db "select * from logs where instr(Msg,'ctag') != 0;" > tmp.txt
#tail tmp.txt
#rm tmp.txt

