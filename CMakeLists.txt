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
