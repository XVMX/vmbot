#!/bin/sh
if command -v curl > /dev/null 2>&1; then
    get="curl -LO"
elif command -v wget > /dev/null 2>&1; then
    get="wget"
else
    echo "Failed to locate network downloader" >&2
    exit 1
fi

$get https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
$get https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2.md5

echo "***"
echo "MD5 check"
echo "***"
if ! md5sum -c sqlite-latest.sqlite.bz2.md5; then
    rm sqlite-latest.sqlite.bz2 sqlite-latest.sqlite.bz2.md5
    exit 1
fi

echo "***"
echo "Extracting archive"
echo "***"
bunzip2 -v sqlite-latest.sqlite.bz2

echo "***"
echo "Creating new database"
echo "***"
sqlite3 sqlite-latest.sqlite ".dump chrFactions" > dump.sql
sqlite3 sqlite-latest.sqlite ".dump mapRegions" >> dump.sql
sqlite3 sqlite-latest.sqlite ".dump mapConstellations" >> dump.sql
sqlite3 sqlite-latest.sqlite ".dump mapSolarSystems" >> dump.sql
sqlite3 sqlite-latest.sqlite ".dump invNames" >> dump.sql
sqlite3 sqlite-latest.sqlite ".dump invTypes" >> dump.sql
sqlite3 staticdata.sqlite < dump.sql

echo "***"
echo "Deleting temporary/downloaded files"
echo "***"
rm dump.sql sqlite-latest.sqlite sqlite-latest.sqlite.bz2.md5

echo "***"
echo "Finished"
echo "***"
