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


class Corne42Tests(unittest.TestCase):
    def setUp(self):
        self.keymap = (CONFIG / 'corne_choc_pro.keymap').read_text()
        self.overlay = (CONFIG / 'corne_choc_pro_42.dtsi').read_text()
        self.points = json.loads((CONFIG / 'corne_choc_pro.json').read_text())['layouts']['default_layout']['layout']

    def test_matrix_and_physical_layout_match_json_on_both_halves(self):
        expected = [(row, col) for row in range(3) for col in (*range(6), *range(8, 14))]
        expected += [(3, col) for col in (3, 4, 5, 8, 9, 10)]
        matrix = [tuple(map(int, p)) for p in re.findall(r'RC\((\d+),(\d+)\)', self.overlay)]
        self.assertEqual(matrix, expected)
        self.assertEqual([(p['row'], p['col']) for p in self.points], expected)
        attrs = re.findall(r'<&key_physical_attrs ([^>]+)>', self.overlay)
        self.assertEqual(len(attrs), 42)
        for point, values in zip(self.points, attrs):
            actual = [int(n) / 100 for n in re.findall(r'-?\d+', values)]
            self.assertEqual(actual, [point.get('w', 1), point.get('h', 1), point['x'], point['y'],
                                     point.get('r', 0), point.get('rx', 0), point.get('ry', 0)])
        right = (ROOT / 'boards/arm/corne_choc_pro/corne_choc_pro_right.dts').read_text()
        self.assertIn('col-offset = <7>', block(right, 'default_transform'))
        self.assertNotIn('col-offset', block(self.overlay, 'default_transform'))

    def test_all_layers_and_studio_use_42_positions(self):
        for name in ('default_layer', 'nav_layer', 'numbol_layer', 'settings_layer'):
            bindings = re.search(r'\bbindings\s*=\s*<([^>]+)>', block(self.keymap, name))[1]
            self.assertEqual(bindings.count('&'), 42, name)
        positions = re.search(r'positions\s*=\s*<([^>]+)>', self.overlay)[1]
        self.assertEqual(list(map(int, positions.split())), list(range(42)))
        self.assertIn('&five_col_layout { status = "disabled"; };', self.overlay)
        self.assertIn('/delete-node/ &five_col_map;', self.overlay)
        self.assertIn('#include "corne_choc_pro_42.dtsi"', self.keymap)
        self.assertNotIn('corne_choc_pro_42.dtsi', (CONFIG / 'corne_choc_pro_5col.keymap').read_text())

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
                             [i for i, p in enumerate(self.points) if (p['col'] >= 8) == opposite_is_right])


if __name__ == '__main__':
    unittest.main()
