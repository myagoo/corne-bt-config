# Personal 42-key Corne configuration

The normal `corne_choc_pro` build has six columns and three thumb keys per half.
The two inner switches on the first two rows of each half are absent (old binding
indices 6, 7, 20 and 21). The four layers now contain 42 bindings; all remaining
bindings, combos and home-row modifier triggers keep their physical switches.

`config/corne_choc_pro_42.dtsi`, included by the keymap, overrides the matrix
transform and physical geometry. PCB row/column numbers and the right half's
column offset stay unchanged. The unused five-column layout is disabled in this
build so ZMK Studio and the physical-key bitmap both use 42 positions. The separate
`corne_choc_pro_5col` builds keep their original configuration.

## Updating the keyboard and Corny

1. Build the normal left and right firmware from `main` using the existing workflow.
2. Flash **both halves**, using `corne_choc_pro_bt_left` and
   `corne_choc_pro_bt_right`. The split link transports logical positions, so
   mixing the old 46-key and new 42-key firmware shifts right-hand bindings.
3. If a keymap was saved through ZMK Studio, restore the firmware's stock keymap
   through Studio before using the new layout: old saved bindings use the old
   indices. Do not use a settings-reset firmware just to update the keymap;
   it also clears Bluetooth pairings.
4. In Corny's configuration, use these two URLs and refresh after flashing:
   - Physical layout: https://raw.githubusercontent.com/myagoo/corne-bt-config/main/config/corne_choc_pro.json
   - Bindings: https://raw.githubusercontent.com/myagoo/corne-bt-config/main/config/corne_choc_pro.keymap

Corny caches these files for offline use. The old bundled layout or files from
`feat/keybeacon` still describe 46 positions; replace them with the `main` URLs.
The physical-key packet remains 8 bytes, now announcing 42 positions (`0x2a`).

## Local checks

```sh
python3 tests/test_corne_42.py
python3 tests/test_physical_keys_native.py  # Requires GCC and GNU ld on Linux.
```

The layout checks cover geometry/matrix agreement, all layer lengths, Studio
mapping, combo coordinates and opposite-hand modifier triggers. The native test
exercises the production C module with a 42-position bitmap, including the last
right-hand position (41). These checks do not replace a Zephyr/ARM build or a
hardware check after flashing.
