#!/usr/bin/env bash
set -euo pipefail
fname="GSF_Emotes.zip"
ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109) Gecko/20100101 Firefox/112.0"

echo "Downloading $fname..."
wget -nv -T 60 -e robots=off -U "$ua" --https-only -r -l 1 -nd \
  -I /images -X /images/archive "https://wiki.goonswarm.org/w/File:$fname"

# Requires GNU sed extensions
echo "Extracting emotes.txt..."
unzip -p "$fname" "gsf/theme" |
  sed '0,/^\[default\]$/Id' > emotes.txt
chmod 444 emotes.txt

echo "Deleting $fname..."
rm "$fname"
echo "Finished"
