#!/bin/bash
set -eu
etag_path="${1:-.ci-etag}"
etag_file="$etag_path/pidgin_nosmile.zip.txt"

echo "Downloading pidgin_nosmile.zip..."
mkdir -p "$etag_path"
touch "$etag_file"
curl -sSLO --etag-compare "$etag_file" --etag-save "$etag_file" \
     https://s3.amazonaws.com/emotes.gbs.io/pidgin_nosmile.zip

if [[ ! -s pidgin_nosmile.zip ]]; then
  echo "emotes.txt is up to date"
  rm pidgin_nosmile.zip
  exit 0
fi

echo "Extracting emotes.txt..."
unzip -p pidgin_nosmile.zip "pidgin_nosmile/theme" > emotes.txt
chmod 444 emotes.txt

echo "Deleting pidgin_nosmile.zip..."
rm pidgin_nosmile.zip

echo "Finished"
