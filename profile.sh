#!/bin/bash

# Copyright (C) 2016 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Statistics
#

echo The distribution of FileKey## as it relates to MAX_DETECT
grep -iPo "filekey\d+" Winapp2.ini  | grep -oP "\d+" | sort -n |uniq -c

echo
echo The distribution of ExcludeKey## as it relates to MAX_DETECT
grep -iPo "excludekey\d+" Winapp2.ini  | grep -oP "\d+" | sort -n |uniq -c


echo
echo Environment variables
grep -iPo "%[^%]+%" Winapp2-combined.ini  | sort | uniq -ci
