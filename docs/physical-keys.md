# Physical key positions over Bluetooth

The optional local Zephyr module exposes held physical binding positions for the
Omarchy Corne typing aid. It does not send keycodes or change keyboard behaviour.
It complements `zmk-keybeacon` v1.2.0 but is a private extension with separate UUIDs.

## Build

`CONFIG_ZMK_PHYSICAL_KEYS=y` is enabled only for the normal
`corne_choc_pro_left` entry in `build.yaml`. The repository's existing GitHub
Actions workflow adds this repository through `ZMK_EXTRA_MODULES`, which loads
`zephyr/module.yml`, the root `Kconfig` and `CMakeLists.txt`. The peripheral half
already sends physical positions to the central; it needs no protocol change.
5-column and settings-reset builds leave the feature disabled.

The normal left build also enables
`CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y`. The right firmware already
enables battery reporting and the standard Bluetooth Battery Service, but ZMK
does not fetch peripheral battery levels on the central by default. This option
makes the central read and subscribe to the right battery, raising the events
that KeyBeacon uses for its right-side percentage and connectivity flag. Without
it, KeyBeacon reports `255` (unavailable) for the right battery even when keys work.
The separate battery proxy service is not needed: KeyBeacon publishes the value.
Enabling fetching requires reflashing the left half only; the existing right
firmware already provides the necessary service.

The implementation targets ZMK v0.3. It uses GNU ld
`--wrap=raise_zmk_position_state_changed` to observe initial physical events
**before** combo and hold-tap listeners can capture or consume them. The wrapper
then calls the original function with the original event and returns its result.
A normal downstream listener would miss some of these physical events.
Captured-event replays (`ZMK_EVENT_RAISE_AT` / `ZMK_EVENT_RELEASE`) bypass the hook;
they must not create artificial presses. LTO is rejected by CMake because it
can bypass linker wrapping. Recheck these call paths when upgrading ZMK.

KeyBeacon v1.2.0 has a CMake probe-output parsing issue: the compatibility check
finds the legacy endpoint API, but its compile definition is lost. The root
`CMakeLists.txt` checks `zmk/endpoints.h` and supplies
`ZMK_KEYBEACON_HAS_LEGACY_ENDPOINT=1` through Zephyr's interface definitions when
the legacy declaration exists. This selects KeyBeacon's existing compatibility
branch without changing its source or upgrading ZMK. Revisit this workaround
when upgrading KeyBeacon.

ZMK's transformed `position` is the zero-based index of a binding in each layer,
not a HID usage or an untransformed row/column. The normal Corne transform has
46 positions; the layout JSON uses the same order. ZMK central forwards events
from the right half in this same namespace. Its split disconnect handler emits
releases for that half's held positions through the same path.

## Service

- Service: `6f8a0000-1c9d-4b53-a6e0-9b1d5f032740`
- Characteristic: `6f8a0001-1c9d-4b53-a6e0-9b1d5f032740`
- Properties: READ and NOTIFY, no writable key data.
- Characteristic reads and CCC reads/writes require an encrypted BLE connection.
- Notifications go to subscribed clients. Opening the typing aid subscribes;
  closing both views unsubscribes. There is no scanning or pairing in the plugin.

Every value is a complete snapshot:

| Byte | Meaning |
| --- | --- |
| 0 | Protocol version, currently `1` |
| 1 | Number of physical positions, `1..128` |
| 2 onward | Bitmap, `ceil(count / 8)` bytes; position `p` is bit `p % 8` of byte `2 + p / 8` |

Unused high bits of the last byte are zero. For this 46-key Corne the packet is
8 bytes. `01 2e 01 00 00 00 00 20` means positions **0 and 45** held;
`01 2e 00 00 00 00 00 00` means all released. The maximum 18-byte packet fits
the default ATT notification payload without MTU negotiation.

The bitmap is independent of the active layer, key behaviour and output endpoint.
READ always returns the current bitmap, including keys held before subscription.
The client subscribes before reading and gives newer notifications priority over
a late initial read response. It clears its state on disconnect and reads again
after resubscribing. A missing service disables highlighting only.

## Scheduling and limits

Physical event handling only updates a spinlock-protected bitmap and queues a
snapshot. GATT sends run on a dedicated work queue; they cannot block the keyboard
event handler. Up to 32 snapshots preserve short presses/releases even when the
worker has not run yet. If full, the queue discards its oldest snapshot while
retaining the newest state. A transient send failure retries the latest state.
Under sustained transport overload some very brief intermediate presses can be
omitted; the protocol reports current held state, not a lossless event history.
No notifications are queued when there are no subscribers. No positions are
logged by the module. The queue and 2 KiB thread stack add RAM usage on the central.

## Verification

Run `python3 tests/test_physical_keys_native.py`. It compiles the actual C module
with GCC and fake RTOS/GATT boundaries, uses the real GNU ld wrapping mechanism,
and checks observation before a consuming handler, event/return preservation,
both halves, multi-key state, release, invalid positions, duplicate events,
short taps, queue overflow, send retry and resubscribe snapshots.

The companion plugin has decoder/lifecycle unit tests, JavaScript highlighting
tests and a private BlueZ D-Bus integration test:

```sh
cd ../omarchy-corne-keymap
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_physical_keys_view.cjs
dbus-run-session -- python3 tests/integration_dbus.py --full --physical
```

These tests do not compile the Zephyr/ARM image or prove hardware behaviour.
Build the normal left UF2 with the existing firmware workflow before flashing.
Then check a press/release on each half, multiple held keys, layer switches,
combo constituents, hold-taps, a right-half disconnect while held, and a host
disconnect/reconnect. Confirm that ordinary typing remains unchanged.
