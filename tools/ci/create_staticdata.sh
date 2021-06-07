#!/bin/bash
set -eu
etag_path="${1:-.ci-etag}"
etag_file="$etag_path/sqlite-latest.sqlite.bz2.txt"

echo "Downloading sqlite-latest.sqlite.bz2..."
mkdir -p "$etag_path"
touch "$etag_file"
curl -sSLO --etag-compare "$etag_file" --etag-save "$etag_file" \
     https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2

if [[ ! -s sqlite-latest.sqlite.bz2 ]]; then
  echo "staticdata.sqlite is up to date"
  rm sqlite-latest.sqlite.bz2
  exit 0
fi

curl -sSLO https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2.md5

echo "Verifying MD5 checksum..."
if ! md5sum -c sqlite-latest.sqlite.bz2.md5; then
    rm sqlite-latest.sqlite.bz2 sqlite-latest.sqlite.bz2.md5
    exit 1
fi

echo -e "\nExtracting sqlite-latest.sqlite..."
bunzip2 -v sqlite-latest.sqlite.bz2

echo "Creating new database..."
for table in "chrFactions" "mapRegions" "mapConstellations" "mapSolarSystems" \
             "staStations" "invNames" "invTypes"; do
  sqlite3 sqlite-latest.sqlite ".dump $table" >> dump.sql
done
sqlite3 staticdata.sqlite < dump.sql
chmod 444 staticdata.sqlite

echo "Deleting temporary files..."
rm dump.sql sqlite-latest.sqlite sqlite-latest.sqlite.bz2.md5

echo "Finished"
