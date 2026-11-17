/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

/* Caller supplies PHYSICAL_KEYS_COUNT and serializes access. */
#define PK_PACKET_SIZE (2 + (PHYSICAL_KEYS_COUNT + 7) / 8)
#define PK_QUEUE_SIZE 32
_Static_assert(PHYSICAL_KEYS_COUNT > 0 && PHYSICAL_KEYS_COUNT <= 128,
               "Physical keys protocol supports 1..128 positions");

struct pk_state {
    uint8_t bitmap[PK_PACKET_SIZE - 2];
    uint8_t queue[PK_QUEUE_SIZE][PK_PACKET_SIZE];
    uint8_t head, count;
};

static inline void pk_snapshot(const struct pk_state *state, uint8_t *packet) {
    packet[0] = 1;
    packet[1] = PHYSICAL_KEYS_COUNT;
    memcpy(packet + 2, state->bitmap, sizeof(state->bitmap));
}

static inline bool pk_update(struct pk_state *state, uint32_t position, bool pressed) {
    if (position >= PHYSICAL_KEYS_COUNT) {
        return false;
    }
    uint8_t *byte = &state->bitmap[position / 8];
    uint8_t mask = 1u << (position % 8);
    if (!!(*byte & mask) == pressed) {
        return false;
    }
    *byte = pressed ? *byte | mask : *byte & ~mask;
    return true;
}

static inline void pk_enqueue(struct pk_state *state) {
    /* Under backpressure drop the oldest snapshot, never the latest release. */
    if (state->count == PK_QUEUE_SIZE) {
        state->head = (state->head + 1) % PK_QUEUE_SIZE;
        state->count--;
    }
    pk_snapshot(state, state->queue[(state->head + state->count) % PK_QUEUE_SIZE]);
    state->count++;
}

static inline bool pk_pop(struct pk_state *state, uint8_t *packet) {
    if (!state->count) {
        return false;
    }
    memcpy(packet, state->queue[state->head], PK_PACKET_SIZE);
    state->head = (state->head + 1) % PK_QUEUE_SIZE;
    state->count--;
    return true;
}
