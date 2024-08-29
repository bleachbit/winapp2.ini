#!/bin/bash

# Copyright (C) 2016, 2024 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Sanity check the file Winapp2.ini
#


import configparser
import sys
import unittest


def check_ini_file(filename):
    cp = configparser.ConfigParser(strict=True)
    try:
        cp.read(filename)
    except (configparser.DuplicateSectionError, configparser.DuplicateOptionError) as e:
        print(e)
        return False
    return True


class TestCheckIni(unittest.TestCase):
    def test_duplicate_section(self):
        # Create the .ini files
        duplicate_section_file = 'test_duplicate_section.ini'
        with open(duplicate_section_file, 'w') as f:
            f.write("[Section1]\n")
            f.write("option1=value1\n")
            f.write("[Section1]\n")  # Duplicate section
            f.write("option2=value2\n")

        self.assertFalse(check_ini_file(duplicate_section_file))

    def test_duplicate_option(self):
        # Create the .ini files
        duplicate_option_file = 'test_duplicate_option.ini'
        with open(duplicate_option_file, 'w') as f:
            f.write("[Section1]\n")
            f.write("option1=value1\n")
            f.write("option1=value2\n")  # Duplicate option in the same section
            f.write("[Section2]\n")
            f.write("option1=value3\n")  # Valid option in a different section

        self.assertFalse(check_ini_file(duplicate_option_file))

    def test_valid(self):
        # Create the .ini files
        valid_file = 'test_valid.ini'
        with open(valid_file, 'w') as f:
            f.write("[Section1]\n")
            f.write("option1=value1\n")
            f.write("[Section2]\n")
            f.write("option2=value2\n")

        self.assertTrue(check_ini_file(valid_file))


if __name__ == "__main__":
    # If no args, print usage
    # If filename passed, run check_ini_file(filename).
    # if --test passed, run unit tests.
    if len(sys.argv) == 1:
        print("Usage: check_ini.py filename.ini")
    elif sys.argv[1] == "--test":
        unittest.main(argv=[sys.argv[0]], exit=False)
    else:
        check_ini_file(sys.argv[1])
