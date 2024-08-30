#!/bin/bash

# Copyright (C) 2014-2018 by Andrew Ziem.  All rights reserved.
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
    dos2unix Winapp2.ini
    git diff Winapp2.ini | less
    git commit Winapp2.ini \
        -m 'Automatic update of Winapp2.ini from upstream GitHub repository' \
        --author="Winapp2.ini community <multiple@winapp2.com>"
fi

ANY_ERRORS=0 # initialize error flag (boolean)

# Verify the Winapp2.ini file has at least 10,000 lines.
if [ `wc -l < Winapp2.ini` -lt 10000 ]; then
    echo "ERROR: Winapp2.ini has less than 10,000 lines"
    exit 1
fi

# Copy Winapp2.ini to Winapp2-BleachBit.ini.
cp Winapp2.ini $OUTPUTINI

sbreak
echo Checking for duplicate keys
DUP_COUNT=`grep -Ph "^\[.*\]" $OUTPUTINI | sort | uniq -d| wc -l`
if [ "$DUP_COUNT" -gt "0" ]; then
    echo "ERROR: duplicate keys detected:"
    grep -Ph "^\[.*\]" $OUTPUTINI | sort | uniq -d
    ANY_ERRORS=1
fi

# example: FileKey1=AppData%\
# example: FileKey1=%AppData\-
# be careful with the character \ in the regular expression
sbreak
echo Checking for malformed environment variable
MISSING_PERCENT=`grep -Pi "^(FileKey|DetectFile)\d*=([^%]|%[a-z]+[^%]\\\\\\\\)" $OUTPUTINI | wc -l`
if [ "$MISSING_PERCENT" -gt "0" ]; then
    echo "ERROR: malformed environment variable"
    grep -Pi "^(FileKey|DetectFile)\d*=([^%]|%[a-z]+[^%]\\\\)" $OUTPUTINI
    ANY_ERRORS=1
fi

sbreak
echo Checking for duplicate sections or duplicate options.
python3 check_ini.py $OUTPUTINI
if [ $? -ne 0 ]; then
    echo "ERROR: check_ini failed"
    ANY_ERRORS=1
fi

sbreak
echo Checking for misspelling of RECURSE/REMOVESELF
RE_COUNT=`grep -iP ^FileKey $OUTPUTINI  | grep "|.*|" | cut -d \| -f 3 | grep -vP "^(RECURSE|REMOVESELF)\s*$" | wc -l`
if [ "$RE_COUNT" -gt "0" ]; then
    echo "ERROR: Found misspelling of RECURSE/REMOVESELF:"
    grep -iP ^FileKey $OUTPUTINI  | grep "|.*|" | cut -d \| -f 3 | grep -vP "^(RECURSE|REMOVESELF)\s*$"
    ANY_ERRORS=1
fi

sbreak
echo Checking for RECURSE/REMOVESELF without pipe
RE_PIPE=`grep -Pi '(?<!\|)(REMOVESELF|RECURSE)' $OUTPUTINI | wc -l`
if [ "$RE_PIPE" -gt "0" ]; then
    echo "ERROR: Found missing pipe:"
    grep -Pi '(?<!\|)(REMOVESELF|RECURSE)' $OUTPUTINI
    ANY_ERRORS=1
fi

# Default= no longer exists upstream.
sbreak
echo Checking for Default=
RE_DEFAULT=`grep -Pi '^Default=' $OUTPUTINI | wc -l`
if [ "$RE_DEFAULT" -gt "0" ]; then
    echo "ERROR: Found Default=:"
    grep -Pi '^Default=' $OUTPUTINI
    ANY_ERRORS=1
fi

sbreak
echo Removing ExcludeKey#=REG
# FIXME: Modify $OUTPUTINI instead
python3 remove_unsupported.py $OUTPUTINI
if [ $? -ne 0 ]; then
    echo "ERROR: remove_unsupported failed"
    ANY_ERRORS=1
fi

sbreak
echo Checking for ExcludeKey#=REG
DK_REG_COUNT=`grep -iP "excludekey\d+=reg\|" $OUTPUTINI | wc -l`
if [ "$DK_REG_COUNT" -gt "0" ]; then
    echo "ERROR: Found unsupported lines:"
    grep -iP "excludekey\d+=reg\|" $OUTPUTINI
    ANY_ERRORS=1
fi

if [ "$ANY_ERRORS" -ne "0" ]; then
    # This error-handling method shows all types of errors
    # before exiting.
    echo " "
    echo "ERROR: Exiting because of error"
    exit 1
fi

sbreak
echo unix2dos
unix2dos $OUTPUTINI
if [ $? -ne 0 ]; then
    echo "ERROR: unix2dos failed"
    exit
fi

sbreak
echo -n "Commit $OUTPUTINI ? (yes/no): "
read update_ini
if [ "$update_ini" = "yes" ]; then
    git commit -m 'Automatic update by processing Winapp2.ini' $OUTPUTINI
else
    echo "Here is the command to do it later"
    echo git commit -m 'Automatic update by processing Winapp2.ini' $OUTPUTINI
fi

