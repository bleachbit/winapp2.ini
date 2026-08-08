#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2008-2026 Andrew Ziem.
#
# This work is licensed under the terms of the GNU GPL, version 3 or
# later.  See the COPYING file in the top-level directory.


"""
Apply BleachBit-specific patches to Winapp2-BleachBit.ini.
"""

import configparser
import os
import re
import sys
import unittest


OPTION_RE = re.compile(r'^([^=]+?)\s*=\s*(.*)$')


class WarningConflictError(Exception):
    """Raised when a patch would overwrite an existing Warning option."""


def parse_patches(patches_path):
    """Read patch sections and options from bleachbit_patches.ini."""
    cp = configparser.RawConfigParser()
    cp.optionxform = str
    cp.read(patches_path)
    return {section: dict(cp[section]) for section in cp.sections()}


def section_bounds(lines, section_name):
    """Return (start, end) line indices for section_name, or None if missing."""
    header = f'[{section_name}]'
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == header:
            start = i
        elif start is not None and line.startswith('['):
            return start, i
    if start is not None:
        return start, len(lines)
    return None


def option_name(line):
    """Return the option name part of an INI option line, or None."""
    match = OPTION_RE.match(line)
    if match is None:
        return None
    return match.group(1).strip()


def insert_options(lines, start, end, options, section_name):
    """Merge patch options into a section, preserving BleachBit.ini formatting.

    Returns the updated end index and a list of Warning conflict descriptions
    for this section, so all conflicts across sections can be reported together.
    """
    conflicts = []
    existing = {}
    for i in range(start + 1, end):
        name = option_name(lines[i])
        if name:
            existing[name] = i

    for opt_name, opt_value in options.items():
        if opt_name == 'Warning' and opt_name in existing:
            conflicts.append(
                f'[{section_name}] already has a Warning; aborting for review.\n'
                f'  existing: {lines[existing[opt_name]].strip()}\n'
                f'  patch:    {opt_name} = {opt_value}'
            )
            continue
        if opt_name in existing:
            lines[existing[opt_name]] = f'{opt_name} = {opt_value}\n'
            continue

        insert_at = start + 1
        for i in range(start + 1, end):
            name = option_name(lines[i])
            if name is None:
                continue
            if name.startswith(('FileKey', 'RegKey', 'ExcludeKey')):
                break
            insert_at = i + 1

        lines.insert(insert_at, f'{opt_name} = {opt_value}\n')
        end += 1

    return end, conflicts


def apply_bleachbit_patches(target_path, patches_path):
    """Apply all patches from patches_path into target_path."""
    patches = parse_patches(patches_path)
    with open(target_path, 'r', encoding='utf-8', newline='') as f:
        lines = f.readlines()

    missing = []
    conflicts = []
    for section, options in patches.items():
        bounds = section_bounds(lines, section)
        if bounds is None:
            missing.append(section)
            continue
        start, end = bounds
        _, section_conflicts = insert_options(lines, start, end, options, section)
        conflicts.extend(section_conflicts)

    if missing:
        print(f'WARNING: patch sections not found in target: {missing}')

    if conflicts:
        raise WarningConflictError(
            '\n\n'.join(conflicts)
        )

    with open(target_path, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(lines)


class TestApplyBleachbitPatches(unittest.TestCase):
    """Tests for apply_bleachbit_patches."""

    def setUp(self):
        """Create small target and patches INI fixtures."""
        self.target_ini = 'test_apply_patches_target.ini'
        self.patches_ini = 'test_apply_patches_patches.ini'

        with open(self.target_ini, 'w', encoding='utf-8') as f:
            f.write('[Windows Taskbar *]\n')
            f.write('LangSecRef = 3025\n')
            f.write('Detect = HKCU\\Software\\Microsoft\\Windows\n')
            f.write('FileKey1 = %AppData%\\Recent|*.URL|RECURSE\n')

        with open(self.patches_ini, 'w', encoding='utf-8') as f:
            f.write('[Windows Taskbar *]\n')
            f.write('Warning = Test warning.\n')

    def tearDown(self):
        """Remove the INI fixtures created in setUp."""
        for path in (self.target_ini, self.patches_ini):
            if os.path.exists(path):
                os.remove(path)

    def test_apply_inserts_warning_before_filekey(self):
        """A Warning option is inserted before the first FileKey/RegKey line."""
        apply_bleachbit_patches(self.target_ini, self.patches_ini)
        with open(self.target_ini, encoding='utf-8') as f:
            lines = f.readlines()

        self.assertEqual(lines[0].strip(), '[Windows Taskbar *]')
        self.assertEqual(lines[1].strip(), 'LangSecRef = 3025')
        self.assertEqual(lines[2].strip(), 'Detect = HKCU\\Software\\Microsoft\\Windows')
        self.assertEqual(lines[3].strip(), 'Warning = Test warning.')
        self.assertTrue(lines[4].startswith('FileKey1'))

    def test_apply_aborts_on_existing_warning(self):
        """When a section already has a Warning, the patch is aborted for review."""
        with open(self.target_ini, 'w', encoding='utf-8') as f:
            f.write('[Windows Taskbar *]\n')
            f.write('Warning = Old warning.\n')
            f.write('FileKey1 = %AppData%\\Recent|*.URL|RECURSE\n')

        with self.assertRaises(WarningConflictError):
            apply_bleachbit_patches(self.target_ini, self.patches_ini)

        with open(self.target_ini, encoding='utf-8') as f:
            content = f.read()

        self.assertIn('Old warning.', content)
        self.assertNotIn('Test warning.', content)

    def test_apply_reports_all_conflicts(self):
        """All Warning conflicts across sections are collected into one error."""
        with open(self.target_ini, 'w', encoding='utf-8') as f:
            f.write('[Windows Taskbar *]\n')
            f.write('Warning = Old warning.\n')
            f.write('FileKey1 = %AppData%\\Recent|*.URL|RECURSE\n')
            f.write('[Another Section *]\n')
            f.write('Warning = Another old warning.\n')
            f.write('FileKey1 = %AppData%\\Foo|*.txt\n')

        with open(self.patches_ini, 'w', encoding='utf-8') as f:
            f.write('[Windows Taskbar *]\n')
            f.write('Warning = Test warning.\n')
            f.write('[Another Section *]\n')
            f.write('Warning = Another test warning.\n')

        with self.assertRaises(WarningConflictError) as cm:
            apply_bleachbit_patches(self.target_ini, self.patches_ini)

        message = str(cm.exception)
        self.assertIn('Old warning.', message)
        self.assertIn('Test warning.', message)
        self.assertIn('Another old warning.', message)
        self.assertIn('Another test warning.', message)

        with open(self.target_ini, encoding='utf-8') as f:
            content = f.read()

        self.assertIn('Old warning.', content)
        self.assertIn('Another old warning.', content)
        self.assertNotIn('Test warning.', content)
        self.assertNotIn('Another test warning.', content)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Usage: apply_bleachbit_patches.py target.ini patches.ini')
    elif sys.argv[1] == '--test':
        unittest.main(argv=[sys.argv[0]], exit=False)
    else:
        try:
            apply_bleachbit_patches(sys.argv[1], sys.argv[2])
        except WarningConflictError as err:
            print(err, file=sys.stderr)
            sys.exit(1)
