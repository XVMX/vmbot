#!/bin/sh
wget https://s3.amazonaws.com/emotes.gbs.io/pidgin_nosmile.zip

echo "***"
echo "Extracting archive"
echo "***"
unzip pidgin_nosmile.zip

echo "***"
echo "Extracting emotes.txt"
echo "***"
cp ./pidgin_nosmile/theme ./emotes.txt

echo "***"
echo "Deleting downloaded files"
echo "***"
rm -r ./pidgin_nosmile ./pidgin_nosmile.zip

echo "***"
echo "Finished"
echo "***"
