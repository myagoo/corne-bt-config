#!/usr/bin/env python3
"""Compile the production C module with fake RTOS/GATT and exercise its public I/O.

This tests event wrapping/transport behaviour, not the Zephyr/ARM firmware build.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STUB = r"""
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <sys/types.h>
#define ARG_UNUSED(x) (void)(x)
struct k_spinlock { int unused; };
typedef int k_spinlock_key_t;
static inline int k_spin_lock(struct k_spinlock *l) { (void)l; return 0; }
static inline void k_spin_unlock(struct k_spinlock *l, int k) { (void)l; (void)k; }
struct k_work { int unused; };
struct k_work_q { int unused; };
struct k_work_delayable { void (*handler)(struct k_work *); };
#define K_WORK_DELAYABLE_DEFINE(name, fn) struct k_work_delayable name = {fn}
#define K_THREAD_STACK_DEFINE(name, size) char name[size]
#define K_THREAD_STACK_SIZEOF(name) sizeof(name)
#define K_NO_WAIT 0
#define K_MSEC(n) (n)
#define CONFIG_ZMK_BLE_THREAD_PRIORITY 5
#define CONFIG_APPLICATION_INIT_PRIORITY 90
extern int pending;
static inline int k_work_reschedule_for_queue(struct k_work_q *q, struct k_work_delayable *w, int d) {
  (void)q; (void)w; (void)d; pending = 1; return 0;
}
static inline void k_work_queue_start(struct k_work_q *q, char *s, size_t n, int p, void *c) {
  (void)q; (void)s; (void)n; (void)p; (void)c;
}
#define SYS_INIT(fn, level, priority) int test_init(void) { return fn(); }
struct zmk_position_state_changed { uint8_t source; uint32_t position; bool state; int64_t timestamp; };
int raise_zmk_position_state_changed(struct zmk_position_state_changed);
#define ZMK_KEYMAP_LEN 42
struct bt_conn { int unused; };
struct bt_gatt_attr {
  ssize_t (*read)(struct bt_conn *, const struct bt_gatt_attr *, void *, uint16_t, uint16_t);
  void (*ccc)(const struct bt_gatt_attr *, uint16_t);
};
#define BT_UUID_DECLARE_128(...) 0
#define BT_UUID_128_ENCODE(...) 0
#define BT_GATT_CHRC_READ 1
#define BT_GATT_CHRC_NOTIFY 2
#define BT_GATT_CCC_NOTIFY 1
#define BT_GATT_PERM_READ_ENCRYPT 1
#define BT_GATT_PERM_WRITE_ENCRYPT 2
#define BT_GATT_PRIMARY_SERVICE(uuid) {0}
#define BT_GATT_CHARACTERISTIC(uuid, props, perm, rd, wr, data) {0}, {.read=rd}
#define BT_GATT_CCC(fn, perm) {.ccc=fn}
#define BT_GATT_SERVICE_DEFINE(name, ...) struct { struct bt_gatt_attr attrs[4]; } name = {{__VA_ARGS__}}
static inline ssize_t bt_gatt_attr_read(struct bt_conn *c, const struct bt_gatt_attr *a, void *b,
 uint16_t n, uint16_t o, const void *v, uint16_t size) {
 (void)c; (void)a; if(o > size) return -1; if(n > size-o) n=size-o;
 memcpy(b, (const char*)v+o, n); return n;
}
int bt_gatt_notify(struct bt_conn *, const struct bt_gatt_attr *, const void *, uint16_t);
"""

MAIN = r"""
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include "physical_keys.c"
int pending, send_error, notifications;
static uint8_t received[512][8];
static struct zmk_position_state_changed expected;
static int processed;
static void read_state(uint8_t *value) {
  assert(physical_keys_svc.attrs[2].read(NULL, &physical_keys_svc.attrs[2], value, 8, 0) == 8);
  assert(value[0] == 1 && value[1] == 42);
}
/* Called by the original event raiser, emulating a consuming combo/hold-tap. */
int test_consumer(struct zmk_position_state_changed event) {
  assert(event.position == expected.position && event.state == expected.state);
  assert(event.source == expected.source && event.timestamp == expected.timestamp);
  uint8_t value[8]; read_state(value);
  if(event.position < 42) assert(!!(value[2+event.position/8] & (1u << (event.position%8))) == event.state);
  processed++;
  return 2; /* ZMK_EV_EVENT_CAPTURED must not prevent physical observation. */
}
static void press(uint8_t source, uint32_t position, bool down) {
  expected = (struct zmk_position_state_changed){source, position, down, 12345};
  assert(raise_zmk_position_state_changed(expected) == 2);
}
int bt_gatt_notify(struct bt_conn *conn, const struct bt_gatt_attr *attr, const void *data, uint16_t len) {
  assert(conn == NULL && attr == &physical_keys_svc.attrs[2] && len == 8);
  if(send_error) return send_error;
  assert(notifications < 512); memcpy(received[notifications++], data, len); return 0;
}
static void drain(void) { pending=0; notify_work.handler(NULL); }
static void subscribe(bool on) { physical_keys_svc.attrs[3].ccc(&physical_keys_svc.attrs[3], on ? 1 : 0); }
int main(void) {
  assert(test_init() == 0);
  uint8_t value[8];
  press(255, 0, true); /* No subscribers: retain current state, send nothing. */
  assert(!pending && notifications == 0);
  read_state(value); assert(value[2] == 1);
  subscribe(true); drain(); assert(received[0][2] == 1);
  press(0, 41, true); press(255, 0, false); press(0, 41, false);
  assert(notifications == 1); /* No GATT operation on the key-processing path. */
  drain(); assert(notifications == 4);
  assert(received[1][2] == 1 && received[1][7] == 2);
  assert(received[2][2] == 0 && received[2][7] == 2);
  assert(received[3][2] == 0 && received[3][7] == 0);
  press(0, 41, false); press(255, 999, true); drain(); assert(notifications == 4);
  /* Short tap snapshots survive even before the worker gets CPU time. */
  press(255, 8, true); press(255, 8, false); drain();
  assert(received[4][3] == 1 && received[5][3] == 0);
  /* Under heavy backpressure, the final release is never discarded. */
  for(int i=0; i<100; i++) press(255, 7, !(i%2));
  drain(); assert(received[notifications-1][2] == 0);
  press(0, 41, true); drain(); /* Split disconnect uses the same release path. */
  press(0, 41, false); drain(); assert(received[notifications-1][7] == 0);
  send_error=-ENOMEM; press(255, 3, true); drain(); assert(pending);
  press(255, 3, false); send_error=0; drain(); assert(received[notifications-1][2] == 0);
  subscribe(false); press(0, 41, true); press(255, 3, true);
  read_state(value); assert(value[2] == 8 && value[7] == 2);
  subscribe(true); drain(); assert(received[notifications-1][2] == 8 && received[notifications-1][7] == 2);
  subscribe(false); press(0, 41, false); press(255, 3, false); subscribe(true); drain();
  assert(received[notifications-1][2] == 0 && received[notifications-1][7] == 0);
  assert(processed > 100);
  puts("Native C: pre-consumer link hook, both halves, multi-key, short taps, overflow, retry and resubscribe passed.");
}
"""

with tempfile.TemporaryDirectory(prefix="corne-physical-native-") as folder:
    folder = Path(folder)
    (folder / "stub.h").write_text(STUB)
    for header in ["zephyr/kernel.h", "zephyr/init.h", "zephyr/bluetooth/gatt.h",
                   "zmk/events/position_state_changed.h", "zmk/matrix.h"]:
        path = folder / header
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#include "stub.h"\n')
    (folder / "main.c").write_text(MAIN)
    (folder / "event.c").write_text('#include "stub.h"\n'
        'extern int test_consumer(struct zmk_position_state_changed);\n'
        'int raise_zmk_position_state_changed(struct zmk_position_state_changed e) { return test_consumer(e); }\n')
    subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
        "-fsanitize=undefined", "-I" + str(folder), "-I" + str(ROOT / "src"),
        str(folder / "main.c"), str(folder / "event.c"),
        "-Wl,--wrap=raise_zmk_position_state_changed", "-o", str(folder / "test")], check=True)
    subprocess.run([str(folder / "test")], check=True)
