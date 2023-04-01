#!/usr/bin/env bash
set -eu
fname="sqlite-latest.sqlite.bz2"

etag_path="${1:-.ci-etag}"
mkdir -p "$etag_path"
etag_file="$etag_path/$fname.txt"

# Requires curl 7.70 or later for bug-free etag support (CI: ubuntu-22.04)
echo "Downloading $fname..."
curl -Z -fsSLO -m 600 --etag-compare "$etag_file" --etag-save "$etag_file" \
     "https://www.fuzzwork.co.uk/dump/$fname" --next \
     -fsSLO -m 120 "https://www.fuzzwork.co.uk/dump/$fname.md5"

if [[ ! -s "$fname" ]]; then
  echo "staticdata.sqlite is up to date"
  rm -f "$fname"{,.md5}
  exit 0
fi

echo "Verifying MD5 checksum..."
if ! md5sum -c "$fname.md5"; then
  rm -f "$fname"{,.md5}
  exit 1
fi

fname="sqlite-latest.sqlite"
echo "Extracting $fname..."
bzip2 -dfv "$fname.bz2"

echo -e "\nCreating new database..."
sqlite3 "$fname" <<EOF | sqlite3 staticdata.sqlite
.bail on
.dump chrFactions
.dump mapRegions
.dump mapConstellations
.dump mapSolarSystems
.dump staStations
.dump invNames
.dump invTypes
EOF

# The full dogma attribute data is >20 MB, but we only need a tiny subset of it.
# So instead we store that data in a non-standard table.
sqlite3 staticdata.sqlite <<EOL
.bail on
ATTACH DATABASE '$fname' AS sde;
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
rm "$fname"{,.bz2.md5}
echo "Finished"
