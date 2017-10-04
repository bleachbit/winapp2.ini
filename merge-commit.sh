#!/bin/bash

# Copyright (C) 2014 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Generate Winapp2-BleachBit.ini
#

UPSTREAMDIR=../Winapp2
OUTPUTINI=Winapp2-BleachBit.ini

sbreak () {
    # Show a section break to make the output easier to read
    echo " "
}

echo git pull here
git pull

sbreak
echo -n "Update upstream? (yes/no): "
read updateupstream
if [ "$updateupstream" = "yes" ]; then
    git -C $UPSTREAMDIR pull
    cp $UPSTREAMDIR/Non-CCleaner/Winapp2.ini .
    git diff Winapp2.ini | less
    git commit Winapp2.ini -m 'Automatic update of Winapp2.ini from upstream GitHub repository'
fi

sbreak
echo Checking for duplicate keys
DUP_COUNT=`grep -Ph "^\[.*\]" Winapp2.ini | sort | uniq -d| wc -l`
if [ "$DUP_COUNT" -gt "0" ]; then
    echo "ERROR: duplicate keys detected:"
    grep -Ph "^\[.*\]" Winapp2.ini | sort | uniq -d
    exit
fi

sbreak
echo Checking for duplicate options within a section
python check_ini.py
if [ $? -ne 0 ]; then
    echo "ERROR: check_ini failed"
    exit 1
fi

sbreak
echo Checking for ExcludeKey#=REG
DK_REG_COUNT=`grep -iP "excludekey\d+=reg\|" Winapp2.ini | wc -l`
if [ "$DK_REG_COUNT" -gt "0" ]; then
    echo "ERROR: Found unsupported lines:"
    grep -iP "excludekey\d+=reg\|" Winapp2.ini
    exit 1
fi


sbreak
echo Removing Default= lines, which are not used by BleachBit
grep -viP "^Default=" Winapp2.ini > body.ini.tmp

sbreak
echo Creating header
echo "; Winapp2.ini for BleachBit" > header.ini.tmp
echo ";  https://github.com/bleachbit/winapp2.ini/" >> header.ini.tmp
echo " " >> header.ini.tmp
echo " " >> header.ini.tmp

sbreak
echo Combining body with header
cat header.ini.tmp body.ini.tmp > $OUTPUTINI
rm *.ini.tmp

sbreak
echo unix2dos
unix2dos $OUTPUTINI
if [ $? -ne 0 ]; then
    echo "ERROR: unix2dos failed"
    exit
fi

sbreak
echo -n "Commit $OUTPUTINI ? (yes/no): "
read updateupstream
if [ "$updateupstream" = "yes" ]; then
    git commit -m 'Automatic update by processing Winapp2.ini' $OUTPUTINI
else
    echo "Here is the command to do it later"
    echo git commit -m 'Automatic update by processing Winapp2.ini' $OUTPUTINI
fi

