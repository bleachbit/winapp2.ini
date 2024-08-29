#!/bin/bash

# Copyright (C) 2024 by Andrew Ziem.  All rights reserved.
# License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
# This is free software: you are free to change and redistribute it.
# There is NO WARRANTY, to the extent permitted by law.
#
# Remove unsupported sections from Winapp2.ini.
#

import configparser
import unittest
import sys
import os


def remove_unsupported(ini_filename):
    r"""
    This reads the specified INI file and removes any section that contains an ExcludeKey#
    (with any number) that starts with REG| such as any below:

    ExcludeKey1=REG|HKCU\Software\MyApp\Settings
    ExcludeKey2=REG|HKCU\Software\MyApp\Preferences
    """
    # Use RawConfigParser to avoid interpolation.
    cp = configparser.RawConfigParser()
    cp.optionxform = str  # Be case sensitive.
    cp.read(ini_filename)

    sections_to_remove = []

    for section in cp.sections():
        for option in cp.options(section):
            if option.lower().startswith("excludekey") and cp.get(section, option).startswith("REG|"):
                sections_to_remove.append(section)
                break

    for section in sections_to_remove:
        cp.remove_section(section)

    with open(ini_filename, 'w') as configfile:
        cp.write(configfile)

    print(f"Removed sections: {sections_to_remove}")


class TestRemoveUnsupported(unittest.TestCase):
    def setUp(self):
        """Create a temporary INI file for testing."""
        self.test_ini_file = 'test_winapp2.ini'
        self.config = configparser.ConfigParser()
        self.config.optionxform = str  # Be case sensitive.

        # Section1 and Section2 should be removed.
        self.config['Section1'] = {
            'ExcludeKey1': 'REG|HKCU\\Software\\MyApp\\Settings',
            'Option1': 'Value1'
        }
        self.config['Section2'] = {
            'ExcludeKey2': 'REG|HKCU\\Software\\MyApp\\Preferences',
            'Option2': 'Value2'
        }
        # Section3 should be preserved.
        self.config['Section3'] = {
            'Option3': 'Value3'
        }

        with open(self.test_ini_file, 'w') as configfile:
            self.config.write(configfile)

    def tearDown(self):
        """Remove the temporary INI file after testing."""
        if os.path.exists(self.test_ini_file):
            os.remove(self.test_ini_file)

    def test_remove_unsupported(self):
        """Test that sections with ExcludeKey# starting with REG| are removed."""
        remove_unsupported(self.test_ini_file)

        modified_config = configparser.ConfigParser()
        modified_config.optionxform = str  # Be case sensitive.
        modified_config.read(self.test_ini_file)

        # Check that Section1 and Section2 have been removed.
        self.assertNotIn('Section1', modified_config.sections())
        self.assertNotIn('Section2', modified_config.sections())
        # Check that Section3 remains.
        self.assertIn('Section3', modified_config.sections())
        self.assertIn('Option3', modified_config['Section3'])


if __name__ == "__main__":
    # If no args, print usage
    # If filename passed, run check_ini_file(filename).
    # if --test passed, run unit tests.
    if len(sys.argv) == 1:
        print("Usage: remove_unsupported.py filename.ini")
    elif sys.argv[1] == "--test":
        unittest.main(argv=[sys.argv[0]], exit=False)
    else:
        remove_unsupported(sys.argv[1])
