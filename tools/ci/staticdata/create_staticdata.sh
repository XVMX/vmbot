#!/bin/bash
set -eu
etag_path="${1:-.ci-etag}"
etag_file="$etag_path/sqlite-latest.sqlite.bz2.txt"

echo "Downloading sqlite-latest.sqlite.bz2..."
mkdir -p "$etag_path"
touch "$etag_file"
curl -fsSLO --etag-compare "$etag_file" --etag-save "${etag_file}.new" \
     https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2
mv "${etag_file}.new" "$etag_file"

if [[ ! -s sqlite-latest.sqlite.bz2 ]]; then
  echo "staticdata.sqlite is up to date"
  rm sqlite-latest.sqlite.bz2
  exit 0
fi

curl -fsSLO https://www.fuzzwork.co.uk/dump/sqlite-latest.sqlite.bz2.md5

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

# The full dogma attribute data is >20 MB, but we only need a tiny subset of it.
# So instead we store that data in a non-standard table.
sqlite3 staticdata.sqlite <<EOL
.bail on
ATTACH DATABASE 'sqlite-latest.sqlite' AS sde;
BEGIN IMMEDIATE;
CREATE TABLE main.market_structures (
  typeID INTEGER NOT NULL PRIMARY KEY
);

-- typeID: 35892 Standup Market Hub I
-- For some reason, CCP stores the integer attribute value in valueFloat
INSERT OR IGNORE INTO main.market_structures
SELECT attrs.valueFloat FROM sde.dgmTypeAttributes attrs
INNER JOIN sde.dgmAttributeTypes types ON attrs.attributeID = types.attributeID
WHERE attrs.typeID = 35892 AND types.attributeName = 'Can be fitted to' AND types.published = 1;
COMMIT;
EOL
chmod 444 staticdata.sqlite

echo "Deleting temporary files..."
rm dump.sql sqlite-latest.sqlite sqlite-latest.sqlite.bz2.md5

echo "Finished"
