#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2008-2026 Andrew Ziem.
#
# This work is licensed under the terms of the GNU GPL, version 3 or
# later.  See the COPYING file in the top-level directory.

"""
Sanity check the file Winapp2.ini that complements BleachBit's native Winapp.py
"""


import configparser
import re
import sys
import unittest


# Valid LangSecRef values, matching bleachbit.Winapp.langsecref_map.
KNOWN_LANGSECREFS = {
    '3001', '3005', '3006',
    '3021', '3022', '3023', '3024', '3025', '3026',
    '3027', '3028', '3029', '3030', '3031', '3033', '3034',
    'Games',
}

# Valid registry hive prefixes, matching bleachbit.Windows.split_registry_key.
REGISTRY_HIVES = {'HKCR', 'HKCU', 'HKLM', 'HKU'}

# Matches numbered option types like FileKey1, DetectFile2, ExcludeKey3.
_NUMBERED_OPTION = re.compile(r'^(filekey|regkey|excludekey|detectfile|detect)(\d+)$')

_DETECTOS_SINGLE = re.compile(r'^\d+\.\d+$')


def _valid_detectos(value):
    """Return True if DetectOS value is well-formed.

    Valid formats: X.Y (exact), X.Y| (min only), |X.Y (max only),
    X.Y|Z.W (range).
    """
    value = value.strip()
    if '|' not in value:
        return bool(_DETECTOS_SINGLE.match(value))
    parts = value.split('|')
    if len(parts) != 2:
        return False
    lo, hi = parts[0].strip(), parts[1].strip()
    if not lo and not hi:
        return False
    if lo and not _DETECTOS_SINGLE.match(lo):
        return False
    if hi and not _DETECTOS_SINGLE.match(hi):
        return False
    return True


def _check_number_gaps(section, options):
    """Return WARNING issues for gaps in numbered option sequences."""
    issues = []
    by_type = {}
    for option in options:
        match = _NUMBERED_OPTION.match(option)
        if match:
            otype, num = match.group(1), int(match.group(2))
            by_type.setdefault(otype, []).append(num)
    for otype, nums in by_type.items():
        nums.sort()
        expected = set(range(1, nums[-1] + 1))
        missing = sorted(expected - set(nums))
        if missing:
            issues.append(('WARNING', section,
                           f'{otype}: gap in numbering, missing {missing}'))
    return issues


def check_structure(cp):
    """Check structural integrity of a parsed winapp2.ini config.

    Returns a list of (severity, section, message) tuples where
    severity is 'ERROR' or 'WARNING'.
    """
    issues = []
    for section in cp.sections():
        options = cp.options(section)

        # unknown LangSecRef value
        if 'langsecref' in options:
            value = cp.get(section, 'langsecref').strip()
            if value not in KNOWN_LANGSECREFS:
                issues.append(('WARNING', section,
                               f'unknown LangSecRef={value!r}'))

        # DetectOS format
        if 'detectos' in options:
            value = cp.get(section, 'detectos')
            if not _valid_detectos(value):
                issues.append(('ERROR', section,
                               f'malformed DetectOS={value!r}'))

        # RegKey hive prefix
        for option in options:
            if option.startswith('regkey'):
                value = cp.get(section, option).strip()
                path = value.split('|')[0]
                hive = path.split('\\', 1)[0] if '\\' in path else path
                if hive not in REGISTRY_HIVES:
                    issues.append(('ERROR', section,
                                   f'{option}: invalid registry hive '
                                   f'{hive!r} in {value!r}'))

        # number gaps in FileKey/RegKey/Detect/DetectFile/ExcludeKey
        issues.extend(_check_number_gaps(section, options))

        # empty section (no FileKey or RegKey)
        has_action = any(o.startswith('filekey') or o.startswith('regkey')
                         for o in options)
        if not has_action:
            issues.append(('WARNING', section,
                           'section has no FileKey or RegKey'))
    return issues


def check_ini_file(filename):
    """Check an INI file for duplicate sections/options and structural errors.

    Returns True if no errors are found, False otherwise.
    Warnings are reported but do not affect the return value.
    """
    # RawConfigParser avoids % interpolation errors on FileKey values.
    # strict=True raises on duplicate sections/options during read().
    cp = configparser.RawConfigParser(strict=True)
    try:
        cp.read(filename)
    except (configparser.DuplicateSectionError,
            configparser.DuplicateOptionError) as e:
        print(e)
        return False

    issues = check_structure(cp)
    errors = [i for i in issues if i[0] == 'ERROR']
    warnings = [i for i in issues if i[0] == 'WARNING']

    for severity, section, message in issues:
        print(f'{severity}: [{section}] {message}')

    if warnings:
        print(f'{len(warnings)} warning(s)')
    if errors:
        print(f'{len(errors)} error(s)')
        return False
    if not warnings and not errors:
        print(f'{filename}: OK')
    return True


class TestCheckIni(unittest.TestCase):
    """Unit tests for check_ini_file and check_structure."""

    def setUp(self):
        """Track temp files for cleanup."""
        self._temp_files = []

    def _write_ini(self, content, filename='test_check_ini.ini'):
        """Write content to a temp INI file and return its path."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self._temp_files.append(filename)
        return filename

    def tearDown(self):
        """Remove temp files."""
        for path in self._temp_files:
            if __import__('os').path.exists(path):
                __import__('os').remove(path)

    def _parse(self, content):
        """Parse content and return (config, issues)."""
        filename = self._write_ini(content)
        cp = configparser.RawConfigParser(strict=True)
        cp.read(filename)
        return cp, check_structure(cp)

    def test_duplicate_section(self):
        """Verify that a duplicate section is detected."""
        filename = self._write_ini(
            "[Section1]\noption1=value1\n[Section1]\noption2=value2\n")

        self.assertFalse(check_ini_file(filename))

    def test_duplicate_option(self):
        """Verify that a duplicate option within a section is detected."""
        filename = self._write_ini(
            "[Section1]\noption1=value1\noption1=value2\n"
            "[Section2]\noption1=value3\n")

        self.assertFalse(check_ini_file(filename))

    def test_valid(self):
        """Verify that a well-formed winapp2 section passes the check."""
        filename = self._write_ini(
            "[SomeApp]\n"
            "LangSecRef=3021\n"
            "FileKey1=%LocalAppData%\\SomeApp|*.log\n")

        self.assertTrue(check_ini_file(filename))

    def test_unknown_langsecref(self):
        """unknown LangSecRef value is a warning."""
        _, issues = self._parse(
            "[BadApp]\nLangSecRef=9999\nFileKey1=%AppData%\\x|*\n")

        warnings = [i for i in issues if i[0] == 'WARNING'
                    and 'LangSecRef' in i[2]]
        self.assertEqual(len(warnings), 1)

    def test_known_langsecref_games(self):
        """the custom 'Games' LangSecRef is accepted."""
        _, issues = self._parse(
            "[My Game]\nLangSecRef=Games\nFileKey1=%AppData%\\x|*\n")

        warnings = [i for i in issues if 'LangSecRef' in i[2]]
        self.assertEqual(len(warnings), 0)

    def test_bad_detectos(self):
        """malformed DetectOS is an error."""
        _, issues = self._parse(
            "[BadApp]\nLangSecRef=3021\nDetectOS=10\n"
            "FileKey1=%AppData%\\x|*\n")

        errors = [i for i in issues if i[0] == 'ERROR']
        self.assertEqual(len(errors), 1)
        self.assertIn('DetectOS', errors[0][2])

    def test_valid_detectos_range(self):
        """a valid DetectOS range passes."""
        _, issues = self._parse(
            "[GoodApp]\nLangSecRef=3021\nDetectOS=6.1|10.0\n"
            "FileKey1=%AppData%\\x|*\n")

        errors = [i for i in issues if 'DetectOS' in i[2]]
        self.assertEqual(len(errors), 0)

    def test_bad_regkey_hive(self):
        """invalid registry hive prefix is an error."""
        _, issues = self._parse(
            "[BadApp]\nLangSecRef=3021\n"
            "RegKey1=HCKU\\Software\\Bad\n")

        errors = [i for i in issues if i[0] == 'ERROR'
                  and 'hive' in i[2]]
        self.assertEqual(len(errors), 1)

    def test_valid_regkey_hive(self):
        """valid hive prefixes pass."""
        _, issues = self._parse(
            "[GoodApp]\nLangSecRef=3021\n"
            "RegKey1=HKCU\\Software\\Good\n")

        errors = [i for i in issues if 'hive' in i[2]]
        self.assertEqual(len(errors), 0)

    def test_filekey_gap(self):
        """gap in FileKey numbering is a warning."""
        _, issues = self._parse(
            "[GapApp]\nLangSecRef=3021\n"
            "FileKey1=%AppData%\\a|*\n"
            "FileKey3=%AppData%\\b|*\n")

        warnings = [i for i in issues if i[0] == 'WARNING'
                    and 'gap' in i[2]]
        self.assertEqual(len(warnings), 1)
        self.assertIn('2', warnings[0][2])

    def test_empty_section(self):
        """section with no FileKey or RegKey is a warning."""
        _, issues = self._parse(
            "[EmptyApp]\nLangSecRef=3021\nDetect=HKCU\\Software\\X\n")

        warnings = [i for i in issues if i[0] == 'WARNING'
                    and 'no FileKey' in i[2]]
        self.assertEqual(len(warnings), 1)


if __name__ == "__main__":
    # If no args, print usage
    # If filename passed, run check_ini_file(filename).
    # if --test passed, run unit tests.
    if len(sys.argv) == 1:
        print("Usage: check_ini.py filename.ini")
    elif sys.argv[1] == "--test":
        unittest.main(argv=[sys.argv[0]], exit=False)
    else:
        sys.exit(0 if check_ini_file(sys.argv[1]) else 1)
