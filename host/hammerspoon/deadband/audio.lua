-- deadband/audio.lua -- AUDIO / PRESENCE module for the Cowork Console.
--
-- The panel is the source of truth for three states:
--
--     toggle_1  -> Do Not Disturb       (ON = focus, OFF = available)
--     toggle_2  -> audio OUTPUT device   (ON = Shure MV7, OFF = External Headphones)
--     paddle    -> microphone mute       (ON = muted, OFF = live)
--
-- The firmware sends a Hyper chord for every edge of these controls. This
-- module binds the matching chords on the host and carries out the action.
--
--     toggle_1 ON  -> Hyper+F13     toggle_1 OFF -> Hyper+F14
--     toggle_2 ON  -> Hyper+F15     toggle_2 OFF -> Hyper+F16
--     paddle   ON  -> Hyper+F17     paddle   OFF -> Hyper+F18
--
-- Reconcile loop: macOS lets other apps and the menu bar move the default
-- output device or change the mute state behind the panel's back. An
-- hs.audiodevice.watcher re-asserts the last-known desired state on drift.
-- The panel wins.
--
-- ---------------------------------------------------------------------------
-- PREREQUISITES
--
-- Do Not Disturb is driven through the macOS Shortcuts CLI (/usr/bin/shortcuts).
-- macOS exposes no first-class scripting hook for Focus modes, so you must
-- create two Shortcuts yourself and name them EXACTLY:
--
--     "Deadband DND On"   -> action: Set Focus -> Do Not Disturb -> On
--     "Deadband DND Off"  -> action: Set Focus -> Do Not Disturb -> Off
--
-- Rename them below (DND.shortcutOn / DND.shortcutOff) if you prefer other
-- names. If the shortcuts CLI is missing the module logs a one-time warning
-- and DND becomes a no-op; everything else keeps working.
--
-- Hammerspoon needs Accessibility permission for keystroke synthesis (used
-- elsewhere) but audio device control and the Shortcuts CLI need none.
--
-- ---------------------------------------------------------------------------

local M = {}

-- Configurable device names. Override from init.lua by reaching into this
-- table before audio.start(ctx), or pass ctx.audio = { outputOn=..., outputOff=... }.
M.DEVICES = {
  outputOn = "Shure MV7",          -- toggle_2 ON
  outputOff = "External Headphones", -- toggle_2 OFF
}

M.DND = {
  shortcutOn = "Deadband DND On",
  shortcutOff = "Deadband DND Off",
}

-- Chord keys for each control edge (see contract above).
local KEYS = {
  dndOn = "f13",
  dndOff = "f14",
  outputOn = "f15",
  outputOff = "f16",
  micMute = "f17",   -- paddle ON  = muted
  micLive = "f18",   -- paddle OFF = live
}

-- ---------------------------------------------------------------------------
-- internal state
-- ---------------------------------------------------------------------------

-- Last-known DESIRED state, as last commanded by the panel. nil means "panel
-- has not spoken since load" -- the reconcile loop leaves those alone.
local desired = {
  outputName = nil,  -- string device name the panel last selected
  inputMuted = nil,  -- boolean the panel last selected
}

local watcher = nil   -- hs.audiodevice.watcher
local shortcutsAvailable = nil  -- cached bool
local banner = nil    -- ctx.banner, optional feedback surface

-- ---------------------------------------------------------------------------
-- helpers
-- ---------------------------------------------------------------------------

local function note(text)
  -- Best-effort feedback. The banner is transient and optional.
  if banner and banner.hint then
    banner.hint(text)
  else
    print("[deadband.audio] " .. text)
  end
end

local function fail(text)
  if banner and banner.fail then
    banner.fail(text)
  else
    print("[deadband.audio] FAIL: " .. text)
  end
end

local function hasShortcutsCli()
  if shortcutsAvailable == nil then
    -- hs.fs.attributes returns nil for a missing path.
    shortcutsAvailable = hs.fs.attributes("/usr/bin/shortcuts") ~= nil
    if not shortcutsAvailable then
      print("[deadband.audio] /usr/bin/shortcuts not found -- DND is a no-op. "
        .. "Install Shortcuts or wire a fallback.")
    end
  end
  return shortcutsAvailable
end

-- ---------------------------------------------------------------------------
-- DND (best-effort; not reconciled)
--
-- Focus state cannot be read back reliably from the command line, so DND has
-- no reconcile loop -- it is fire-and-forget. If a Focus schedule or another
-- app flips DND, the panel will only correct it on the next toggle edge. This
-- is a known and accepted limitation.
-- ---------------------------------------------------------------------------

local function runShortcut(name)
  if not hasShortcutsCli() then return end
  -- Single-quote the name; shortcut names here contain no single quotes.
  local cmd = string.format([[/usr/bin/shortcuts run '%s']], name)
  -- Run async so a slow Shortcut never blocks the Hammerspoon event loop.
  hs.task.new("/bin/sh", function(code, _, stderr)
    if code ~= 0 then
      fail(string.format("Shortcut '%s' exited %d: %s", name, code, (stderr or ""):gsub("%s+$", "")))
    end
  end, { "-c", cmd }):start()
end

local function setDnd(on)
  runShortcut(on and M.DND.shortcutOn or M.DND.shortcutOff)
  note(on and "DND on" or "DND off")
end

-- ---------------------------------------------------------------------------
-- OUTPUT device
-- ---------------------------------------------------------------------------

local function applyOutput(name)
  local dev = hs.audiodevice.findOutputByName(name)
  if not dev then
    fail(string.format("Output device not found: %q", name))
    return false
  end
  -- setDefaultOutputDevice returns true on success.
  local ok = dev:setDefaultOutputDevice()
  if not ok then
    fail(string.format("Could not set output to %q", name))
    return false
  end
  return true
end

local function setOutput(name)
  desired.outputName = name
  if applyOutput(name) then
    note("Output -> " .. name)
  end
end

-- ---------------------------------------------------------------------------
-- MIC mute
-- ---------------------------------------------------------------------------

local function applyInputMuted(muted)
  local dev = hs.audiodevice.defaultInputDevice()
  if not dev then
    fail("No default input device")
    return false
  end
  -- setInputMuted returns true if the device supports muting and it took.
  local ok = dev:setInputMuted(muted)
  if ok == false then
    fail("Default input device does not support mute")
    return false
  end
  return true
end

local function setInputMuted(muted)
  desired.inputMuted = muted
  if applyInputMuted(muted) then
    note(muted and "Mic muted" or "Mic live")
  end
end

-- ---------------------------------------------------------------------------
-- reconcile loop -- the panel is boss
-- ---------------------------------------------------------------------------

local function reconcile()
  -- OUTPUT: if reality drifted from the panel's last selection, re-assert.
  if desired.outputName then
    local current = hs.audiodevice.defaultOutputDevice()
    if not current or current:name() ~= desired.outputName then
      applyOutput(desired.outputName)
    end
  end

  -- INPUT: re-assert mute state on the current default input device.
  if desired.inputMuted ~= nil then
    local dev = hs.audiodevice.defaultInputDevice()
    if dev and dev:inputMuted() ~= desired.inputMuted then
      dev:setInputMuted(desired.inputMuted)
    end
  end
end

-- ---------------------------------------------------------------------------
-- public API
-- ---------------------------------------------------------------------------

-- M.start(ctx) -- bind the six toggle chords and start the reconcile watcher.
-- ctx fields used: ctx.chords.bind (required), ctx.banner (optional),
-- ctx.audio (optional overrides: outputOn, outputOff, dndOn, dndOff).
function M.start(ctx)
  ctx = ctx or {}
  banner = ctx.banner

  -- Apply optional overrides from init.lua's config block.
  if ctx.audio then
    if ctx.audio.outputOn then M.DEVICES.outputOn = ctx.audio.outputOn end
    if ctx.audio.outputOff then M.DEVICES.outputOff = ctx.audio.outputOff end
    if ctx.audio.dndOn then M.DND.shortcutOn = ctx.audio.dndOn end
    if ctx.audio.dndOff then M.DND.shortcutOff = ctx.audio.dndOff end
  end

  local bind = ctx.chords and ctx.chords.bind
  if not bind then
    error("[deadband.audio] ctx.chords.bind is required")
  end

  -- toggle_1 -> Do Not Disturb
  bind(KEYS.dndOn, function() setDnd(true) end)
  bind(KEYS.dndOff, function() setDnd(false) end)

  -- toggle_2 -> audio output device
  bind(KEYS.outputOn, function() setOutput(M.DEVICES.outputOn) end)
  bind(KEYS.outputOff, function() setOutput(M.DEVICES.outputOff) end)

  -- paddle -> mic mute (ON = muted)
  bind(KEYS.micMute, function() setInputMuted(true) end)
  bind(KEYS.micLive, function() setInputMuted(false) end)

  -- Reconcile loop: re-assert panel state when the OS or another app moves it.
  -- The watcher callback fires on every audio subsystem event; reconcile is
  -- cheap and idempotent, so we run it unconditionally.
  watcher = hs.audiodevice.watcher
  watcher.setCallback(function(_) reconcile() end)
  watcher.start()

  return M
end

-- M.stop() -- tear down the reconcile watcher. Bindings persist (Hammerspoon
-- hotkeys are released on full config reload).
function M.stop()
  if watcher then
    watcher.stop()
  end
end

return M
