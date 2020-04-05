#!/bin/bash

# Copyright (C) 2016-2018 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Statistics
#

echo "The distribution of FileKey## (formerly for MAX_DETECT)"
grep -iPo "filekey\d+" Winapp2.ini  | grep -oP "\d+" | sort -n |uniq -c

echo
echo "The distribution of ExcludeKey## (formerly for MAX_DETECT)"
grep -iPo "excludekey\d+" Winapp2.ini  | grep -oP "\d+" | sort -n |uniq -c

echo
echo "The values for SpecialDetect"
grep -iP "^SpecialDetect=" Winapp2.ini  | sort -n |uniq -c

echo
echo Environment variables
grep -iPo "%[^%]+%" Winapp2.ini | sort | uniq -ci

echo
echo DetectOS
grep -i detectos= Winapp2-BleachBit.ini | sort |uniq -c

echo
echo LangSecRef
grep -i langsecref= Winapp2-BleachBit.ini | sort |uniq -c
