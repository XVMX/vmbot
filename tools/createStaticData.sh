#!/bin/sh
wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2.md5
wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
if [ "$(md5sum sqlite-latest.sqlite.bz2)" != "$(cat sqlite-latest.sqlite.bz2.md5)" ]; then
    echo "MD5SUM mismatch"
    rm sqlite-latest.sqlite.bz2 sqlite-latest.sqlite.bz2.md5
    exit
else
    echo "MD5SUM match"
fi

echo "***"
echo "Extracting archive"
echo "***"
bunzip2 sqlite-latest.sqlite.bz2

echo "***"
echo "Dumping tables"
echo "***"
sqlite3 sqlite-latest.sqlite ".dump mapSolarSystems" > dump.sql
sqlite3 sqlite-latest.sqlite ".dump mapConstellations" >> dump.sql
sqlite3 sqlite-latest.sqlite ".dump mapRegions" >> dump.sql
sqlite3 sqlite-latest.sqlite ".dump invTypes" >> dump.sql
sqlite3 staticdata.sqlite < dump.sql

echo "***"
echo "Deleting downloaded files"
echo "***"
rm dump.sql sqlite-latest.sqlite sqlite-latest.sqlite.bz2.md5

echo "Finished"
