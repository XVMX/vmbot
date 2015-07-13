#!/bin/sh
wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2.md5
wget https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
md5sum -c sqlite-latest.sqlite.bz2.md5
 
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
