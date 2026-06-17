-- deadband/banner.lua
--
-- On-screen feedback. HID is one-way: the panel can light its own button LED but
-- it cannot read the host, so the screen is where outcomes are reported. The
-- banner is the one thing on screen that tells the truth about a running job.
--
-- Built on hs.canvas -- a single centered plate near the bottom of the main
-- screen. Understated on purpose. The brand is dry and precise; the banner is a
-- status line, not a notification.
--
-- States and lifetimes:
--   arm(text)     transient   ~10s -- "armed, press Launch" (matches the dial timer)
--   hint(text)    transient   ~1.2s -- "turn to arm" nudge on a stray press
--   running(text) persistent  -- stays until done/fail replaces it
--   done(text)    transient   ~2.5s -- success outcome
--   fail(text)    transient   ~2.5s -- failure outcome
--
-- Any call replaces whatever is showing. running() is the only state that does
-- not self-dismiss; it waits for an outcome.

local M = {}

-- -- timing (seconds) ------------------------------------------------------
local ARM_TTL  = 10.0
local HINT_TTL = 1.2
local DONE_TTL = 2.5

-- -- palette ---------------------------------------------------------------
-- Restrained. Red is reserved for failure only, mirroring the panel's rule that
-- #ea2a1f means hazard/live and nothing else.
local PLATE   = { red = 0.04, green = 0.04, blue = 0.05, alpha = 0.92 }
local BORDER  = { red = 1.00, green = 1.00, blue = 1.00, alpha = 0.10 }
local NEUTRAL = { red = 0.92, green = 0.92, blue = 0.92, alpha = 1.00 }
local MUTED   = { red = 0.60, green = 0.60, blue = 0.62, alpha = 1.00 }
local GOOD    = { red = 0.62, green = 0.86, blue = 0.62, alpha = 1.00 }
local BAD     = { red = 0.92, green = 0.17, blue = 0.12, alpha = 1.00 }  -- #ea2a1f

local FONT = "JetBrains Mono"          -- falls back to the system mono if absent
local FALLBACK_FONT = "Menlo"

-- -- internal state --------------------------------------------------------
local canvas = nil
local dismissTimer = nil

local function chosenFont()
  -- hs.styledtext tolerates an unknown font name (it substitutes), but we prefer
  -- the panel's mono if it is installed.
  local installed = hs.styledtext.fontNames and hs.styledtext.fontNames() or nil
  if installed then
    for _, name in ipairs(installed) do
      if name == FONT then return FONT end
    end
    return FALLBACK_FONT
  end
  return FONT
end

local function cancelDismiss()
  if dismissTimer then
    dismissTimer:stop()
    dismissTimer = nil
  end
end

local function teardown()
  cancelDismiss()
  if canvas then
    canvas:delete()
    canvas = nil
  end
end

-- Lay out and show the plate. ttl == nil keeps it up indefinitely (running).
local function draw(text, color, ttl)
  cancelDismiss()

  local screen = hs.screen.mainScreen()
  local frame = screen:frame()

  local width = 520
  local height = 56
  local x = frame.x + (frame.w - width) / 2
  local y = frame.y + frame.h - height - 96   -- floated above the Dock

  if not canvas then
    canvas = hs.canvas.new({ x = x, y = y, w = width, h = height })
    canvas:level(hs.canvas.windowLevels.overlay)
    canvas:behaviorAsLabels({ "canJoinAllSpaces", "stationary" })
  else
    canvas:frame({ x = x, y = y, w = width, h = height })
  end

  local styled = hs.styledtext.new(text, {
    font = { name = chosenFont(), size = 15 },
    color = color,
    paragraphStyle = { alignment = "center" },
  })

  canvas:replaceElements(
    {
      type = "rectangle",
      action = "fill",
      fillColor = PLATE,
      roundedRectRadii = { xRadius = 10, yRadius = 10 },
    },
    {
      type = "rectangle",
      action = "stroke",
      strokeColor = BORDER,
      strokeWidth = 1,
      roundedRectRadii = { xRadius = 10, yRadius = 10 },
    },
    {
      type = "text",
      text = styled,
      frame = { x = 0, y = 18, w = width, h = height - 18 },
    }
  )

  canvas:show()

  if ttl then
    dismissTimer = hs.timer.doAfter(ttl, function()
      teardown()
    end)
  end
end

-- -- public API ------------------------------------------------------------

-- Armed: a launcher is selected and waiting for the Launch press. Persists for
-- the arming window, then clears itself if nothing fires.
function M.arm(text)
  draw(text, NEUTRAL, ARM_TTL)
end

-- Hint: a stray Launch press with nothing armed. Brief, muted.
function M.hint(text)
  draw(text, MUTED, HINT_TTL)
end

-- Running: a job is in flight. Persists until done() or fail() replaces it.
function M.running(text)
  draw(text, NEUTRAL, nil)
end

-- Done: success outcome. Self-dismisses.
function M.done(text)
  draw(text, GOOD, DONE_TTL)
end

-- Fail: failure outcome. Self-dismisses. The only state that uses the red.
function M.fail(text)
  draw(text, BAD, DONE_TTL)
end

-- Clear immediately. Not part of the contract surface but handy for teardown.
function M.clear()
  teardown()
end

return M
