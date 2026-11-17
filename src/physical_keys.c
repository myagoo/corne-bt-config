/* SPDX-License-Identifier: MIT */
#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/init.h>
#include <zephyr/bluetooth/gatt.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/matrix.h>

#define PHYSICAL_KEYS_COUNT ZMK_KEYMAP_LEN
#include "physical_keys_state.h"

/* Private extension, deliberately outside KeyBeacon's UUID namespace. */
#define PK_UUID(value) BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(value, 0x1c9d, 0x4b53, 0xa6e0, 0x9b1d5f032740))
static struct pk_state state;
static struct k_spinlock state_lock;
static bool subscribed, ready;
static struct k_work_q notify_queue;
K_THREAD_STACK_DEFINE(notify_stack, 2048);
static void send_pending(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(notify_work, send_pending);

static void schedule_notify(void) {
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    bool send = ready && subscribed && state.count;
    k_spin_unlock(&state_lock, key);
    if (send) {
        k_work_reschedule_for_queue(&notify_queue, &notify_work, K_NO_WAIT);
    }
}

static ssize_t read_positions(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                              void *buf, uint16_t len, uint16_t offset) {
    uint8_t packet[PK_PACKET_SIZE];
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    pk_snapshot(&state, packet);
    k_spin_unlock(&state_lock, key);
    return bt_gatt_attr_read(conn, attr, buf, len, offset, packet, sizeof(packet));
}

static void subscription_changed(const struct bt_gatt_attr *attr, uint16_t value) {
    ARG_UNUSED(attr);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    subscribed = value == BT_GATT_CCC_NOTIFY;
    state.head = state.count = 0;
    if (subscribed) {
        pk_enqueue(&state);
    }
    k_spin_unlock(&state_lock, key);
    schedule_notify();
}

BT_GATT_SERVICE_DEFINE(physical_keys_svc,
    BT_GATT_PRIMARY_SERVICE(PK_UUID(0x6f8a0000)),
    BT_GATT_CHARACTERISTIC(PK_UUID(0x6f8a0001), BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
                           BT_GATT_PERM_READ_ENCRYPT, read_positions, NULL, NULL),
    BT_GATT_CCC(subscription_changed, BT_GATT_PERM_READ_ENCRYPT | BT_GATT_PERM_WRITE_ENCRYPT));

static void send_pending(struct k_work *work) {
    ARG_UNUSED(work);
    uint8_t packet[PK_PACKET_SIZE];
    for (;;) {
        k_spinlock_key_t key = k_spin_lock(&state_lock);
        bool send = subscribed && pk_pop(&state, packet);
        k_spin_unlock(&state_lock, key);
        if (!send) {
            return;
        }
        /* A separate queue keeps GATT buffer waits away from keyboard processing. */
        int err = bt_gatt_notify(NULL, &physical_keys_svc.attrs[2], packet, sizeof(packet));
        if (err) {
            key = k_spin_lock(&state_lock);
            state.head = state.count = 0;
            bool retry = subscribed && err != -ENOTCONN;
            if (retry) {
                pk_enqueue(&state);
            }
            k_spin_unlock(&state_lock, key);
            if (retry) {
                k_work_reschedule_for_queue(&notify_queue, &notify_work, K_MSEC(100));
            }
            return;
        }
    }
}

int __real_raise_zmk_position_state_changed(struct zmk_position_state_changed event);

int __wrap_raise_zmk_position_state_changed(struct zmk_position_state_changed event) {
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    if (pk_update(&state, event.position, event.state) && subscribed) {
        pk_enqueue(&state);
    }
    k_spin_unlock(&state_lock, key);
    schedule_notify();
    /* Preserve the original event, timing and return value. No keycode inference. */
    return __real_raise_zmk_position_state_changed(event);
}

static int physical_keys_init(void) {
    k_work_queue_start(&notify_queue, notify_stack, K_THREAD_STACK_SIZEOF(notify_stack),
                       CONFIG_ZMK_BLE_THREAD_PRIORITY, NULL);
    k_spinlock_key_t key = k_spin_lock(&state_lock);
    ready = true;
    k_spin_unlock(&state_lock, key);
    schedule_notify();
    return 0;
}
SYS_INIT(physical_keys_init, APPLICATION, CONFIG_APPLICATION_INIT_PRIORITY);
