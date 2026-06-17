-- deadband/init.lua
--
-- Entry point for the Deadband Cowork Console host integration.
--
-- The panel presents to macOS as a USB HID device emitting Hyper chords. macOS
-- handles media (encoder) and screen lock (button long-press) natively. This
-- Hammerspoon tree binds everything else: the six toggle/paddle chords drive
-- audio and presence (audio.lua), and the twelve rotary chords plus the Launch
-- tap drive the arming/dispatch state machine (rotary.lua + dispatch.lua).
--
-- INSTALL
--   Hammerspoon loads ~/.hammerspoon/init.lua and resolves require() against
--   ~/.hammerspoon/. Put this tree where it can be found, then load it.
--
--   1. Symlink (or copy) this directory into ~/.hammerspoon:
--        ln -s \
--          "<repo>/host/hammerspoon/deadband" \
--          ~/.hammerspoon/deadband
--
--   2. From your own ~/.hammerspoon/init.lua, require it:
--        require("deadband")
--
--      (require("deadband") loads this file. If you would rather not commit to
--      a require path, dofile the absolute path instead:
--        dofile(os.getenv("HOME") .. "/.hammerspoon/deadband/init.lua")  )
--
--   3. Reload Hammerspoon. Grant Accessibility permission when prompted --
--      dispatch.lua drives the Claude desktop app via System Events keystrokes,
--      and that needs Hammerspoon listed under
--      System Settings > Privacy & Security > Accessibility.
--
-- This module returns ctx so a host init can inspect or extend it.

-- ======================================================================
-- CONFIG -- edit these to match the machine.
-- ======================================================================
local CONFIG = {
  -- Audio device names exactly as they appear in System Settings > Sound.
  -- toggle_2 flips the default output between these two.
  outputDeviceA = "External Headphones",  -- toggle_2 OFF
  outputDeviceB = "Shure MV7",             -- toggle_2 ON

  -- macOS Shortcuts used for Do Not Disturb. DND has no first-class Hammerspoon
  -- API, so toggle_1 shells out to `shortcuts run`. Create these two Shortcuts
  -- (each a single Set Focus action) and put their exact names here. If the
  -- Shortcuts are absent, audio.lua falls back and documents the limitation.
  dndOnShortcut  = "Deadband DND On",
  dndOffShortcut = "Deadband DND Off",

  -- The Cowork host application, for activation/targeting. The app is not
  -- AppleScript-scriptable, so dispatch.lua drives it through System Events.
  coworkApp = "Claude",
}
-- ======================================================================

-- Module resolution: these requires assume the tree lives at
-- ~/.hammerspoon/deadband/ (see INSTALL above), so each sibling is
-- "deadband.<name>".
local chords   = require("deadband.chords")
local banner   = require("deadband.banner")
local dispatch = require("deadband.dispatch")
local audio    = require("deadband.audio")
local rotary   = require("deadband.rotary")

-- The shared context every behavior module receives. Built once here so the
-- modules wire against the same chord table, banner, and dispatcher.
--
-- ctx.audio translates the operator-facing CONFIG into the field names audio.lua
-- expects (outputOn/outputOff/dndOn/dndOff). Note the cross-over: toggle_2 ON
-- selects output B (Shure) and OFF selects output A (Headphones), so A/B map to
-- OFF/ON, not 1:1.
local ctx = {
  hyper    = chords.HYPER,
  chords   = chords,
  banner   = banner,
  dispatch = dispatch,
  config   = CONFIG,
  audio    = {
    outputOn  = CONFIG.outputDeviceB,   -- toggle_2 ON  -> Shure MV7
    outputOff = CONFIG.outputDeviceA,   -- toggle_2 OFF -> External Headphones
    dndOn     = CONFIG.dndOnShortcut,
    dndOff    = CONFIG.dndOffShortcut,
  },
}

-- dispatch.lua keeps its own app-name state and is called directly by rotary
-- (not handed ctx), so push the configured app name in explicitly. This keeps
-- CONFIG.coworkApp live rather than cosmetic.
if dispatch.configure then
  dispatch.configure({ app = CONFIG.coworkApp })
end

-- Bring up the two behavior subsystems. audio binds the six toggle/paddle
-- chords and runs the device-reconcile loop; rotary binds the twelve dial
-- chords and the Launch tap, and drives dispatch.
audio.start(ctx)
rotary.start(ctx)

hs.printf("[deadband] cowork console loaded -- audio + rotary bound")

return ctx
