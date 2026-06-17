-- deadband/chords.lua
--
-- The chord vocabulary. The panel speaks to the host as a USB HID device
-- emitting collision-proof Hyper chords (Command+Control+Option+Shift held
-- with one key). macOS has no Hyper key; the firmware builds it from the four
-- modifiers, and Hammerspoon binds the exact same set. Nothing else on the
-- system uses these combinations, so the chords never collide.
--
-- This module is the single source of truth for which key carries which signal.
-- If a chord changes here it must change in examples/cowork_chords.py too --
-- the firmware sends, Hammerspoon binds, and the two tables must agree.

local M = {}

-- Hyper. Held together with a key, this is the panel's private channel.
M.HYPER = { "cmd", "ctrl", "alt", "shift" }

-- Rotary positions 1..12 map to these keys, in order. The firmware sends the
-- key for the dial's position; index here is the position (1-based).
--   1->1  2->2 ... 9->9  10->0  11->-  12->=
M.ROTARY_KEYS = { "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=" }

-- Toggle / paddle chords. Each control sends a distinct key for ON and OFF.
-- Bound by physical keyCode (numbers), NOT character: function keys (F13-F18)
-- carry an `fn` flag that breaks the match, and character names resolve through
-- the active keyboard layout (so on Colemak/Dvorak "o" is a different physical
-- key than the firmware's O). The firmware sends fixed letter HID usages
-- (U I O P J K) that always land on these keyCodes on every layout. audio.lua
-- binds these.
M.TOGGLE_1_ON  = 32  -- U
M.TOGGLE_1_OFF = 34  -- I
M.TOGGLE_2_ON  = 31  -- O
M.TOGGLE_2_OFF = 35  -- P
M.PADDLE_ON    = 38  -- J
M.PADDLE_OFF   = 40  -- K

-- Button tap. (Long-press lock is sent natively by the firmware as Cmd+Ctrl+Q
-- and never reaches Hammerspoon, so it is intentionally absent from this table.)
M.BUTTON_TAP = "space"

-- bind(key, fn) -> binds Hyper+key to fn and returns the hs.hotkey handle.
-- fn takes no arguments. Use this for the fixed single-key chords above.
function M.bind(key, fn)
  return hs.hotkey.bind(M.HYPER, key, fn)
end

-- bindRotary(fn) -> binds every rotary key to fn(position), where position is
-- the 1..12 index into ROTARY_KEYS. Returns an array of the hotkey handles,
-- index-aligned with ROTARY_KEYS. The position is captured at bind time, so
-- each handler reports its own slot.
function M.bindRotary(fn)
  local handles = {}
  for position, key in ipairs(M.ROTARY_KEYS) do
    handles[position] = hs.hotkey.bind(M.HYPER, key, function()
      fn(position)
    end)
  end
  return handles
end

return M
