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
import fnmatch
import os
import re
import sys
import unittest


OPTION_RE = re.compile(r'^([^=]+?)\s*=\s*(.*)$')

# Characters that make a patch section name eligible for glob matching when
# no target section has the exact name. This lets a single patch entry
# (e.g. "[* Saved Usernames & Passwords *]") apply to many sections.
_GLOB_CHARS = frozenset('*?[')


class WarningConflictError(Exception):
    """Raised when a patch would overwrite an existing Warning option."""


def parse_patches(patches_path):
    """Read patch sections and options from bleachbit_patches.ini."""
    cp = configparser.RawConfigParser()
    cp.optionxform = str
    cp.read(patches_path)
    return {section: dict(cp[section]) for section in cp.sections()}


def all_section_bounds(lines):
    """Return an ordered dict {section_name: (start, end)} for every section."""
    sections = {}
    current_name = None
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            if current_name is not None:
                sections[current_name] = (start, i)
            current_name = stripped[1:-1]
            start = i
    if current_name is not None:
        sections[current_name] = (start, len(lines))
    return sections


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


def matching_sections(lines, pattern):
    """Return target sections matching pattern, preferring an exact match."""
    bounds = section_bounds(lines, pattern)
    if bounds:
        return [(pattern, *bounds)]
    if not any(ch in pattern for ch in _GLOB_CHARS):
        return []
    return [
        (name, start, end)
        for name, (start, end) in all_section_bounds(lines).items()
        if fnmatch.fnmatchcase(name, pattern)
    ]


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
            existing_match = OPTION_RE.match(lines[existing[opt_name]])
            existing_value = existing_match.group(2).strip() if existing_match else ''
            if existing_value == opt_value:
                continue
            # This is a meta-warning: a warning about a warning. However, the
            # warning warning aborts the script, so be warned: it is more
            # specifically a warning-error because it will abort `merge-commit.sh`
            # from commiting.
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
        # Glob patterns expand to every matching section, in document order.
        # Targets are re-resolved by name on each iteration so that inserts
        # in earlier sections (which shift line numbers) are accounted for.
        names = [n for n, _s, _e in matching_sections(lines, section)]
        if not names:
            missing.append(section)
            continue
        for name in names:
            bounds = section_bounds(lines, name)
            if bounds is None:
                continue
            start, end = bounds
            _, section_conflicts = insert_options(
                lines, start, end, options, name)
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

    def test_apply_skips_identical_warning(self):
        """An identical existing Warning is silently skipped, not a conflict."""
        with open(self.target_ini, 'w', encoding='utf-8') as f:
            f.write('[Windows Taskbar *]\n')
            f.write('Warning = Test warning.\n')
            f.write('FileKey1 = %AppData%\\Recent|*.URL|RECURSE\n')

        apply_bleachbit_patches(self.target_ini, self.patches_ini)

        with open(self.target_ini, encoding='utf-8') as f:
            content = f.read()

        self.assertEqual(content.count('Warning = Test warning.'), 1)

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

    def test_glob_applies_warning_to_all_matching_sections(self):
        """A glob patch section name applies to every matching target section."""
        with open(self.target_ini, 'w', encoding='utf-8') as f:
            f.write('[Brave Saved Usernames & Passwords *]\n')
            f.write('Section = Brave Web Browser\n')
            f.write('FileKey1 = %LocalAppData%\\Brave\\User Data\\*|Login Data*\n')
            f.write('[Chromium Saved Usernames & Passwords *]\n')
            f.write('Section = Chromium Web Browser\n')
            f.write('FileKey1 = %LocalAppData%\\Chromium\\User Data\\*|Login Data*\n')
            f.write('[Mozilla Firefox Saved Usernames & Passwords *]\n')
            f.write('Section = Mozilla Firefox Web Browser\n')
            f.write('FileKey1 = %AppData%\\Mozilla\\Firefox\\Profiles\\*|key4.db;logins.json\n')
            f.write('[Brave History *]\n')
            f.write('Section = Brave Web Browser\n')
            f.write('FileKey1 = %LocalAppData%\\Brave\\User Data\\*|History*\n')

        with open(self.patches_ini, 'w', encoding='utf-8') as f:
            f.write('[* Saved Usernames & Passwords *]\n')
            f.write('Warning = This will delete all saved passwords for this browser.\n')

        apply_bleachbit_patches(self.target_ini, self.patches_ini)

        with open(self.target_ini, encoding='utf-8') as f:
            content = f.read()

        # Each password section gained the warning, inserted before FileKey1.
        self.assertEqual(content.count('Warning = This will delete all saved passwords for this browser.'), 3)
        self.assertIn('Warning = This will delete all saved passwords for this browser.\n'
                      'FileKey1 = %LocalAppData%\\Brave\\User Data\\*|Login Data*', content)
        self.assertIn('Warning = This will delete all saved passwords for this browser.\n'
                      'FileKey1 = %LocalAppData%\\Chromium\\User Data\\*|Login Data*', content)
        self.assertIn('Warning = This will delete all saved passwords for this browser.\n'
                      'FileKey1 = %AppData%\\Mozilla\\Firefox\\Profiles\\*|key4.db;logins.json', content)
        # The non-matching Brave History section is untouched.
        self.assertNotIn('Warning = This will delete', content.split('[Brave History *]')[1])

    def test_glob_collects_conflicts_across_matched_sections(self):
        """A glob patch aborts when any matched section already has a Warning."""
        with open(self.target_ini, 'w', encoding='utf-8') as f:
            f.write('[Brave Saved Usernames & Passwords *]\n')
            f.write('FileKey1 = %LocalAppData%\\Brave\\User Data\\*|Login Data*\n')
            f.write('[Chromium Saved Usernames & Passwords *]\n')
            f.write('Warning = Old Chromium warning.\n')
            f.write('FileKey1 = %LocalAppData%\\Chromium\\User Data\\*|Login Data*\n')

        with open(self.patches_ini, 'w', encoding='utf-8') as f:
            f.write('[* Saved Usernames & Passwords *]\n')
            f.write('Warning = New warning.\n')

        with self.assertRaises(WarningConflictError) as cm:
            apply_bleachbit_patches(self.target_ini, self.patches_ini)

        message = str(cm.exception)
        self.assertIn('Old Chromium warning.', message)
        self.assertIn('New warning.', message)
        self.assertIn('[Chromium Saved Usernames & Passwords *]', message)

        # The conflict aborts the whole merge: no section is modified.
        with open(self.target_ini, encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('New warning.', content)

    def test_glob_with_no_matches_is_reported_missing(self):
        """A glob that matches nothing is reported as missing, not an error."""
        with open(self.patches_ini, 'w', encoding='utf-8') as f:
            f.write('[* Nonexistent Section *]\n')
            f.write('Warning = Unused.\n')

        # No exception; the missing patch is just reported on stdout.
        apply_bleachbit_patches(self.target_ini, self.patches_ini)

        with open(self.target_ini, encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('Unused.', content)

    def test_matching_sections_literal_vs_glob(self):
        """Exact section names take precedence over otherwise matching globs."""
        lines = [
            '[Foo Saved Usernames & Passwords *]\n',
            'FileKey1 = x\n',
            '[Foo Saved Usernames & Passwords extra]\n',
            'FileKey1 = extra\n',
            '[Bar Saved Usernames & Passwords *]\n',
            'FileKey1 = y\n',
            '[Baz History *]\n',
            'FileKey1 = z\n',
        ]
        literal = matching_sections(lines, 'Foo Saved Usernames & Passwords *')
        self.assertEqual(len(literal), 1)
        self.assertEqual(literal[0][0], 'Foo Saved Usernames & Passwords *')

        glob = matching_sections(lines, '* Saved Usernames & Passwords *')
        self.assertEqual({name for name, _s, _e in glob},
                         {'Foo Saved Usernames & Passwords *',
                          'Foo Saved Usernames & Passwords extra',
                          'Bar Saved Usernames & Passwords *'})

        none = matching_sections(lines, '* No Such Section *')
        self.assertEqual(none, [])


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
