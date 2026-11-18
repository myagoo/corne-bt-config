#!/usr/bin/env python3
"""Check the physical coordinates, matrix, bindings and positional behaviours agree."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'


def block(text, name):
    start = re.search(r'\b' + name + r'\s*\{', text).end()
    depth = 1
    for end in range(start, len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[start:end]
    raise ValueError(f'Unclosed block: {name}')


class CorneLayoutTests(unittest.TestCase):
    def setUp(self):
        self.keymap = (CONFIG / 'corne_choc_pro.keymap').read_text()
        self.board = (ROOT / "boards/arm/corne_choc_pro/corne_choc_pro.dtsi").read_text()
        self.geometry = (ROOT / "boards/arm/corne_choc_pro/corne_choc_pro-layouts.dtsi").read_text()
        self.points = json.loads((CONFIG / 'corne_choc_pro.json').read_text())['layouts']['default_layout']['layout']

    def test_matrix_and_physical_layout_match_json_on_both_halves(self):
        expected = [(row, col) for row in range(2) for col in range(14)]
        expected += [(2, col) for col in (*range(6), *range(8, 14))]
        expected += [(3, col) for col in (3, 4, 5, 8, 9, 10)]
        matrix = [tuple(map(int, p)) for p in re.findall(r'RC\((\d+),(\d+)\)', block(self.board, 'keymap_transform_0'))]
        self.assertEqual(matrix, expected)
        self.assertEqual([(p['row'], p['col']) for p in self.points], expected)
        attrs = re.findall(r'<&key_physical_attrs ([^>]+)>', block(self.geometry, 'default_layout'))
        self.assertEqual(len(attrs), 46)
        for point, values in zip(self.points, attrs):
            actual = [int(n) / 100 for n in re.findall(r'-?\d+', values)]
            self.assertEqual(actual, [point.get('w', 1), point.get('h', 1), point['x'], point['y'],
                                     point.get('r', 0), point.get('rx', 0), point.get('ry', 0)])
        right = (ROOT / 'boards/arm/corne_choc_pro/corne_choc_pro_right.dts').read_text()
        self.assertIn('col-offset = <7>', block(right, 'default_transform'))

    def test_absent_switches_are_none_without_renumbering_other_keys(self):
        for name in ('default_layer', 'nav_layer', 'numbol_layer', 'settings_layer'):
            bindings = re.search(r'\bbindings\s*=\s*<([^>]+)>', block(self.keymap, name))[1]
            entries = [entry.strip() for entry in re.findall(r'&[^&]+', bindings)]
            self.assertEqual(len(entries), 46, name)
            for index in (6, 7, 20, 21):
                self.assertEqual(entries[index], '&none', (name, index))
        self.assertNotIn('corne_choc_pro_42.dtsi', self.keymap)
        self.assertIn('zmk,physical-layout = &default_layout', self.keymap)

    def test_combos_keep_their_physical_switches(self):
        expected = {
            'left_curly_brace': [(0, 4), (0, 5)], 'right_curly_brace': [(0, 9), (0, 8)],
            'left_paren': [(1, 4), (1, 5)], 'right_paren': [(1, 9), (1, 8)],
            'left_bracket': [(2, 4), (2, 5)], 'right_bracket': [(2, 9), (2, 8)],
            'double_quotes': [(0, 9), (0, 10)], 'single_quote': [(1, 9), (1, 10)],
            'BACKTICK': [(2, 9), (2, 10)], 'eacute': [(0, 3), (0, 4)],
            'egrave': [(0, 3), (0, 2)], 'slash': [(0, 4), (1, 4)],
            'backslash': [(0, 9), (1, 9)], 'less': [(1, 4), (2, 4)],
            'greater': [(1, 9), (2, 9)], 'agrave': [(0, 1), (0, 0)],
        }
        for name, coords in expected.items():
            indices = re.search(r'key-positions\s*=\s*<([^>]+)>', block(self.keymap, name))[1]
            self.assertEqual([(self.points[int(i)]['row'], self.points[int(i)]['col'])
                              for i in indices.split()], coords, name)

    def test_home_row_modifiers_trigger_only_from_the_opposite_half(self):
        for name, opposite_is_right in [('hrm_left', True), ('hrm_left_repeat', True), ('hrm_right', False)]:
            indices = re.search(r'hold-trigger-key-positions\s*=\s*<([^>]+)>', block(self.keymap, name))[1]
            self.assertEqual(list(map(int, indices.split())),
                             [i for i, p in enumerate(self.points) if i not in (6, 7, 20, 21) and (p['col'] >= 8) == opposite_is_right])


if __name__ == '__main__':
    unittest.main()
