#!/bin/bash

# Copyright (C) 2016 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Sanity check the file Winapp2.ini
#


import ConfigParser
from collections import OrderedDict


# handle multiple values for same key
# http://stackoverflow.com/questions/15848674/how-to-configparse-a-file-keeping-multiple-values-for-identical-keys
class MultiOrderedDict(OrderedDict):

    def __setitem__(self, key, value):
        if isinstance(value, list) and key in self:
            self[key].extend(value)
        else:
            super(OrderedDict, self).__setitem__(key, value)

# As a quick hack, use two instances because the multi returns
# no sections and no options, while the multi does not preserve
# multiple values for duplicate key names.

# m = multi
cf_m = ConfigParser.ConfigParser(dict_type=MultiOrderedDict)

# s = single
cf_s = ConfigParser.ConfigParser()

cf_s.read('Winapp2.ini')
cf_m.read('Winapp2.ini')

found_errors = False

for section in cf_s.sections():
    options = cf_s.options(section)
    for option in options:
        value = cf_m.get(section, option)
        l = len(value)
        if l > 1:
            found_errors = True
            print 'Duplicate option %s in section %s' % (option, section)

if found_errors:
    import sys
    sys.exit(1)
