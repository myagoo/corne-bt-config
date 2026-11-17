if(CONFIG_ZMK_KEYBEACON)
  # KeyBeacon 1.2.0's probe detects this API, but its CMake list parser loses
  # the emitted define after the status banner's unmatched '[' character.
  # Use Zephyr's interface definitions so the dependency receives the flag.
  file(READ "${CMAKE_SOURCE_DIR}/include/zmk/endpoints.h" corne_endpoints_header)
  if(corne_endpoints_header MATCHES "zmk_endpoints_selected\\(void\\)")
    zephyr_compile_definitions(ZMK_KEYBEACON_HAS_LEGACY_ENDPOINT=1)
  endif()
endif()

if(CONFIG_ZMK_PHYSICAL_KEYS)
  if(CONFIG_LTO)
    message(FATAL_ERROR "ZMK_PHYSICAL_KEYS requires LTO disabled for linker wrapping")
  endif()
  zephyr_library()
  zephyr_library_include_directories(${CMAKE_SOURCE_DIR}/include)
  zephyr_library_sources(src/physical_keys.c)
  # Capture initial raises before consuming listeners (combos, hold-taps).
  # Captured-event replays bypass this function and must not affect the bitmap.
  zephyr_link_libraries("-Wl,--wrap=raise_zmk_position_state_changed")
endif()
