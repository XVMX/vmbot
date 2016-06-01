#!/bin/sh
if command -v curl > /dev/null 2>&1; then
    get="curl -LO"
elif command -v wget > /dev/null 2>&1; then
    get="wget"
else
    echo "Failed to locate network downloader" >&2
    exit 1
fi

$get https://s3.amazonaws.com/emotes.gbs.io/pidgin_nosmile.zip

echo "***"
echo "Extracting emotes.txt"
echo "***"
unzip -p pidgin_nosmile.zip "pidgin_nosmile/theme" > emotes.txt
chmod 644 emotes.txt

echo "***"
echo "Deleting downloaded archive"
echo "***"
rm pidgin_nosmile.zip

echo "***"
echo "Finished"
echo "***"
