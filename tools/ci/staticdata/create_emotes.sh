#!/usr/bin/env bash
set -euo pipefail
fname="GSF_Emotes.zip"

etag_path="${1:-.ci-etag}"
mkdir -p "$etag_path"
etag_file="$etag_path/$fname.txt"

# Requires curl 7.70 or later for bug-free etag support (CI: ubuntu-22.04)
echo "Downloading $fname..."
curl -fsSLO -m 300 --etag-compare "$etag_file" --etag-save "$etag_file" \
     "https://wiki.goonswarm.org/images/0/0f/$fname"

if [[ ! -s "$fname" ]]; then
  echo "emotes.txt is up to date"
  rm -f "$fname"
  exit 0
fi

# Requires GNU sed extensions
echo "Extracting emotes.txt..."
unzip -p "$fname" "gsf/theme" |
  sed '0,/^\[default\]$/Id' > emotes.txt
chmod 444 emotes.txt

echo "Deleting $fname..."
rm "$fname"
echo "Finished"
