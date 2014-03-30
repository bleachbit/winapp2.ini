#!/bin/bash

# Copyright (C) 2014 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Generate Winapp2-combined.ini
#

echo git pull
git pull

echo cat
cat Winapp2.ini removed-entries.ini > Winapp2-combined.ini

echo Removing Default= lines, which are not used by BleachBit
grep -viP "^Default=" Winapp2-combined.ini >Winapp2-combined.tmp

echo Counting
ENTRY_COUNT=`grep "\[" Winapp2-combined.tmp | wc -l`
echo $ENTRY_COUNT entries

echo Creating header
echo "; Winapp2.ini for BleachBit" > Winapp2-combined.header
echo ";  A combination of www.winapp2.com's winapp2.ini plus extra entries" >> Winapp2-combined.header
echo ";  $ENTRY_COUNT entries" >> Winapp2-combined.header
echo ";  https://github.com/az0/winapp2.ini/" >> Winapp2-combined.header
echo " " >> Winapp2-combined.header
echo " " >> Winapp2-combined.header

echo Combining body with header
cat Winapp2-combined.header Winapp2-combined.tmp > Winapp2-combined.ini
rm Winapp2-combined.{header,tmp}

echo unix2dos
unix2dos Winapp2-combined.ini
if [ $? -ne 0 ]; then
    echo "ERROR: unix2dos failed"
    exit
fi

echo Checking for duplicate keys
DUP_COUNT=`grep -Ph "^\[.*\]" Winapp2.ini removed-entries.ini  | sort | uniq -d| wc -l`
if [ "$DUP_COUNT" -gt "0" ]; then
    echo "ERROR: duplicate keys detected:"
    grep -Ph "^\[.*\]" Winapp2.ini removed-entries.ini  | sort | uniq -d
    exit
fi

echo "git commit (in 5 seconds)"
sleep 5
git commit -m 'Automatic update by combining Winapp2.ini plus removed-entries.ini' Winapp2-combined.ini

echo git push
git push
