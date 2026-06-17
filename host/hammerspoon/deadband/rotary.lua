-- rotary.lua - the arming state machine for the rotary + Launch button.
--
-- The panel sends one Hyper chord per rotary position (Hyper+1..12) and a
-- distinct Hyper+Space when the Launch button is tapped. This module turns
-- those two streams into a deliberate launcher: a turn arms a position and
-- raises a banner; a tap within the window fires the armed launcher; a tap
-- outside the window is a no-op with a faint hint.
--
-- One-way HID means the panel cannot be lit from here. The button's solid-
-- while-held and 5-flash-on-release feedback is driven by the firmware, not
-- this module. The only feedback this module owns is the on-screen banner.
--
-- The long-press lock (button hold -> Command+Control+Q) is sent natively by
-- the firmware and never reaches Hammerspoon. Do not bind it here.
--
-- Encoder media never touches this module either - it is native consumer HID.

local M = {}

-- How long an armed position stays live before it lapses, in seconds.
-- Matches the design doc: turn arms, 10s window, tap fires, lapse disarms.
local ARM_WINDOW = 10

-- Module-local state. A single armed position and a single timer that clears
-- it. Both are nil when nothing is armed.
local armed = nil
local lapseTimer = nil

-- disarm clears the armed position and stops the lapse timer. Idempotent.
local function disarm()
    armed = nil
    if lapseTimer then
        lapseTimer:stop()
        lapseTimer = nil
    end
end

function M.start(ctx)
    -- Reset state on (re)start so a config reload never leaves a stale arm.
    disarm()

    -- Rotary turn: arm the new position. Turning again before firing re-arms
    -- to the new position and resets the window - arming is a fresh act every
    -- time, even back to the same slot. A turn never cancels a running job.
    ctx.chords.bindRotary(function(pos)
        armed = pos
        ctx.banner.arm(ctx.dispatch.labelFor(pos) .. " \194\183 Press Launch to initiate")

        -- Refresh the single lapse timer. Reuse the existing one if present so
        -- we keep exactly one timer alive at a time.
        if lapseTimer then
            lapseTimer:setDelay(ARM_WINDOW)
        else
            lapseTimer = hs.timer.delayed.new(ARM_WINDOW, function()
                -- Window lapsed with no press: drop the arm and let the
                -- transient arm banner fade on its own.
                armed = nil
                lapseTimer = nil
            end)
        end
        lapseTimer:start()
    end)

    -- Button tap (Hyper+Space): fire the armed launcher if the window is still
    -- live, otherwise hint. Capture and clear the armed position before running
    -- so the dispatch (which may be async) cannot be double-fired by a re-entry.
    ctx.chords.bind("space", function()
        if armed then
            local pos = armed
            disarm()
            ctx.dispatch.run(pos, ctx.banner)
        else
            ctx.banner.hint("Turn to arm")
        end
    end)
end

return M
