#!/bin/sh
wget https://s3.amazonaws.com/emotes.gbs.io/pidgin_nosmile.zip

echo "***"
echo "Extracting emotes.txt"
echo "***"
unzip -p ./pidgin_nosmile.zip "pidgin_nosmile/theme" > ./emotes.txt
chmod 644 ./emotes.txt

echo "***"
echo "Deleting downloaded files"
echo "***"
rm ./pidgin_nosmile.zip

echo "***"
echo "Finished"
echo "***"
