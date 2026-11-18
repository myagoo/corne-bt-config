# Personal Corne layout

The firmware keeps the board's original 46 logical positions. The four absent
inner switches (positions 6, 7, 20 and 21) are bound to `&none` on every layer.
Corny hides `&none` keys without removing their physical indices. Transparent
`&trans` keys remain visible.

The 42-position transform has been removed. The current bindings from the
`easier layout` change are preserved, and combos and home-row modifier triggers
use the original position numbering again. The separate five-column build is
unchanged.

## Update

Flash **both halves** with `corne_choc_pro_bt_left` and
`corne_choc_pro_bt_right` built from `main`: mixing 42-position and 46-position
firmware makes the split halves disagree about key indices. No settings-reset
firmware is needed for this update.

Refresh these sources in Corny after flashing:

- Physical layout: https://raw.githubusercontent.com/myagoo/corne-bt-config/main/config/corne_choc_pro.json
- Bindings: https://raw.githubusercontent.com/myagoo/corne-bt-config/main/config/corne_choc_pro.keymap

Corny stores the files offline. Its physical-key stream now has 46 positions
again, including the four hidden, unbound positions.

## Checks

```sh
python3 tests/test_corne_layout.py
python3 tests/test_physical_keys_native.py  # GCC and GNU ld on Linux
```

These checks validate geometry, layer lengths, absent bindings, combo and
modifier positions, and the native physical-key stream. Test typing on hardware
after flashing; the earlier Y/U/K/L failure was not confirmed to be caused by
stored Studio settings.
