-- dispatch.lua - the 12-position launcher bank.
--
-- The rotary selects one of twelve deliberate launchers; the button fires the
-- armed one. This module owns what each slot does. rotary.lua handles the
-- arm/fire ritual and calls M.run(pos, banner) when the owner commits.
--
-- Three kinds of launcher:
--
--   launch            A direct host action - open a URL, focus an app. Fast,
--                     and we mostly know whether it worked.
--   cowork_stateless  A Claude Cowork job that owns its own prompt text. We
--                     bring Cowork forward, paste the prompt, submit.
--   cowork_stateful   A named, recurring Cowork job with history. We bring
--                     Cowork forward and submit a re-run prompt that names the
--                     job - a blank re-run would lose its context.
--
-- A note on honesty. There is no CLI and no usable URL scheme for triggering a
-- named Cowork job today (see the DISCOVERY notes below). Cowork slots drive the
-- desktop UI through osascript: activate the app, paste the prompt, press Return.
-- That is fire-and-forget. We cannot read the outcome back, so a Cowork slot
-- reports DISPATCHED, not DONE - the same truth the panel's LED tells with its
-- five flashes. Only slots we can actually verify report a real DONE/FAILED.
--
-- Run model: every launcher runs async on an hs.task so a slow osascript never
-- blocks the Hammerspoon event loop or the next arm. M.run drives the banner:
-- running(...) on dispatch, then done(...)/fail(...) on completion.

local M = {}

-- == Configuration ====================================================

-- The desktop app that hosts Claude Cowork. Confirmed app name for activation
-- and System Events targeting is "Claude" (/Applications/Claude.app). The app
-- is NOT AppleScript-scriptable, so every interaction goes through System Events
-- GUI keystrokes, never app-specific verbs.
local CLAUDE_APP = "Claude"

-- Milliseconds to let the Claude window come forward before we paste. The app
-- has to be frontmost for the System Events keystroke to land in its composer.
local CLAUDE_FOCUS_DELAY_MS = 600

-- == osascript helper =================================================

-- Run an AppleScript snippet via hs.task (async, non-blocking). Calls
-- cb(ok, stdout, stderr) on completion. ok is true only on a clean exit.
local function osascript(script, cb)
    local task = hs.task.new("/usr/bin/osascript", function(code, stdout, stderr)
        if cb then cb(code == 0, stdout or "", stderr or "") end
    end, { "-e", script })
    task:start()
end

-- Escape a Lua string for safe embedding inside a double-quoted AppleScript
-- string literal. Backslashes and double-quotes are the only characters
-- AppleScript treats specially inside a quoted literal.
local function escapeForAppleScript(s)
    s = s:gsub("\\", "\\\\")
    s = s:gsub('"', '\\"')
    return s
end

-- == Cowork dispatch (UI automation) ==================================

-- DISCOVERY (host facts, 2026-06-16): coworkTrigger = ui_automation_only.
--
-- No CLI subcommand and no usable URL scheme exists for triggering a named
-- Cowork job. The `claude` CLI is Claude Code only - `claude cowork` is not a
-- command. The Claude.app registers the claude:// scheme but only handles
-- auth callbacks and claude://cowork/shared-artifact?uuid=<uuid> (which opens
-- an already-finished shared artifact - NOT a job launcher). There is no
-- claude://cowork/new|start|run|task|resume route.
--
-- So we drive the desktop UI. Clipboard paste is far more reliable than
-- per-character `keystroke` for long or multiline prompts, so we:
--   1. activate / focus the Claude app
--   2. wait for the window to come forward
--   3. set the clipboard to the prompt, paste it (Cmd+V)
--   4. press Return (key code 36) to submit
--
-- Caveats this carries:
--   * Hammerspoon must hold macOS Accessibility permission to send System
--     Events keystrokes to Claude. Without it, the paste/Return silently fail.
--   * There is no programmatic selector for a SPECIFIC named Cowork task. For
--     stateful jobs we submit a prompt that NAMES the job and asks Cowork to
--     resume it, rather than pretending we can click a task in the sidebar.
--     If you keep each named job pinned as the default Cowork view, this lands
--     in the right place; otherwise navigate to the task first by hand.
--   * Fire-and-forget: we get no completion signal back, so the caller reports
--     DISPATCHED rather than a verified DONE.
--
-- TO COLLAPSE THIS LATER: if a real trigger ships (a `claude cowork run <name>`
-- CLI, or a claude://cowork/run?... deep link), replace the body of coworkRun
-- with that one clean call and let the caller report a real outcome.

-- coworkRun(promptOrJobName, isStateful, cb)
--   promptOrJobName : for stateless slots, the full prompt to paste.
--                     for stateful slots, the human name of the recurring job.
--   isStateful      : true selects the named-job resume phrasing.
--   cb(ok)          : invoked once the paste+submit sequence has been sent.
--                     ok reflects only that the keystrokes were delivered, NOT
--                     that the Cowork job succeeded - we cannot know that.
local function coworkRun(promptOrJobName, isStateful, cb)
    local prompt
    if isStateful then
        -- Name the recurring job so Cowork resumes it with its history intact.
        prompt = "Resume the Cowork job named \""
            .. promptOrJobName
            .. "\" and run today's update."
    else
        prompt = promptOrJobName
    end

    local pasteScript = escapeForAppleScript(prompt)

    -- Step 1: bring the app forward.
    osascript('tell application "' .. CLAUDE_APP .. '" to activate', function(activated)
        if not activated then
            if cb then cb(false) end
            return
        end

        -- Step 2: let the window settle, then paste and submit.
        hs.timer.doAfter(CLAUDE_FOCUS_DELAY_MS / 1000, function()
            local script = table.concat({
                'set the clipboard to "' .. pasteScript .. '"',
                'tell application "System Events" to tell process "' .. CLAUDE_APP .. '"',
                '    keystroke "v" using command down',
                '    delay 0.15',
                '    key code 36',  -- Return: submit
                'end tell',
            }, "\n")
            osascript(script, function(ok)
                if cb then cb(ok) end
            end)
        end)
    end)
end

-- == Direct launchers (verifiable) ====================================

-- Open Gmail's compose view in the default browser. We can confirm the URL
-- handoff, so this slot reports a real outcome.
local function openGmailCompose(cb)
    local ok = hs.urlevent.openURL("https://mail.google.com/mail/?view=cm&fs=1")
    if cb then cb(ok == true) end
end

-- Focus Claude Desktop and open a new conversation with Cmd+N. Requires
-- Accessibility permission for the System Events keystroke.
local function newChat(cb)
    osascript('tell application "' .. CLAUDE_APP .. '" to activate', function(activated)
        if not activated then
            if cb then cb(false) end
            return
        end
        hs.timer.doAfter(CLAUDE_FOCUS_DELAY_MS / 1000, function()
            local script = 'tell application "System Events" to tell process "'
                .. CLAUDE_APP .. '" to keystroke "n" using command down'
            osascript(script, function(ok)
                if cb then cb(ok) end
            end)
        end)
    end)
end

-- == The 12-position bank =============================================

-- Each entry: { label, kind, run }.
--   label : the banner text for this slot.
--   kind  : "launch" | "cowork_stateless" | "cowork_stateful".
--   run   : function(cb) -> calls cb(ok). For cowork kinds, ok means
--           "dispatched", not "succeeded" - M.run reports accordingly.
M.LAUNCHERS = {
    -- 1
    {
        label = "GMAIL",
        kind = "launch",
        run = function(cb) openGmailCompose(cb) end,
    },
    -- 2
    {
        label = "NEW CHAT",
        kind = "launch",
        run = function(cb) newChat(cb) end,
    },
    -- 3
    {
        label = "MORNING BRIEF",
        kind = "cowork_stateful",
        run = function(cb) coworkRun("Daily Morning Brief", true, cb) end,
    },
    -- 4
    {
        label = "TIDY DESKTOP",
        kind = "cowork_stateless",
        run = function(cb)
            coworkRun(
                "Organize the files on my Desktop (~/Desktop) into sensible folders.",
                false, cb)
        end,
    },
    -- 5
    {
        label = "TIDY DOWNLOADS",
        kind = "cowork_stateless",
        run = function(cb)
            coworkRun(
                "Organize the files in my Downloads folder (~/Downloads) into sensible folders.",
                false, cb)
        end,
    },
    -- 6
    {
        label = "PSALMLOG DAILY UPDATE",
        kind = "cowork_stateful",
        run = function(cb) coworkRun("Psalmlog Daily Update", true, cb) end,
    },

    -- 7-12: open Cowork slots. Reserved for additional jobs.
    --
    -- TO FILL A SLOT, replace the placeholder below with either:
    --
    --   Stateless (the slot owns its prompt):
    --     {
    --         label = "WEEKLY REVIEW",
    --         kind = "cowork_stateless",
    --         run = function(cb)
    --             coworkRun("Draft my weekly review from this week's notes.", false, cb)
    --         end,
    --     }
    --
    --   Stateful (a named recurring Cowork job with history):
    --     {
    --         label = "INBOX TRIAGE",
    --         kind = "cowork_stateful",
    --         run = function(cb) coworkRun("Inbox Triage", true, cb) end,
    --     }
    --
    -- The placeholder run is a no-op that only nudges the owner. M.run detects
    -- the missing real action and shows banner.hint instead of firing anything.

    -- 7
    {
        label = "OPEN 7",
        kind = "cowork_stateless",
        placeholder = true,
        run = function(cb) if cb then cb(false) end end,
    },
    -- 8
    {
        label = "OPEN 8",
        kind = "cowork_stateless",
        placeholder = true,
        run = function(cb) if cb then cb(false) end end,
    },
    -- 9
    {
        label = "OPEN 9",
        kind = "cowork_stateless",
        placeholder = true,
        run = function(cb) if cb then cb(false) end end,
    },
    -- 10
    {
        label = "OPEN 10",
        kind = "cowork_stateless",
        placeholder = true,
        run = function(cb) if cb then cb(false) end end,
    },
    -- 11
    {
        label = "OPEN 11",
        kind = "cowork_stateless",
        placeholder = true,
        run = function(cb) if cb then cb(false) end end,
    },
    -- 12
    {
        label = "OPEN 12",
        kind = "cowork_stateless",
        placeholder = true,
        run = function(cb) if cb then cb(false) end end,
    },
}

-- == Public API =======================================================

-- M.configure(opts) -- apply operator config from init.lua. Accepts:
--   app          : the Cowork host app name for activation/targeting.
--   focusDelayMs : ms to wait after activate before pasting.
-- Reassigns the module upvalues so every launcher (coworkRun, newChat) picks up
-- the change at call time.
function M.configure(opts)
    opts = opts or {}
    if opts.app then CLAUDE_APP = opts.app end
    if opts.focusDelayMs then CLAUDE_FOCUS_DELAY_MS = opts.focusDelayMs end
end

-- M.labelFor(pos) -> the banner label for a 1..12 position, or a fallback.
function M.labelFor(pos)
    local entry = M.LAUNCHERS[pos]
    if entry then return entry.label end
    return "POS " .. tostring(pos)
end

-- M.run(pos, banner)
--   Fire the launcher at position pos (1..12). Runs async; drives the banner:
--   running(...) on dispatch, then done(...) / fail(...) on completion.
--
--   Honesty rule: a cowork_* slot is fire-and-forget UI automation. We cannot
--   read the job's true outcome, so a delivered dispatch reports done("DISPATCHED").
--   A launch slot reports a real done("DONE") / fail("FAILED") because we can
--   observe whether the host action took.
function M.run(pos, banner)
    local entry = M.LAUNCHERS[pos]
    if not entry then
        if banner then banner.fail("No launcher at " .. tostring(pos)) end
        return
    end

    -- Unfilled placeholder: never pretend to fire. Nudge and stop.
    if entry.placeholder then
        if banner then banner.hint(entry.label .. " is empty - wire it in dispatch.lua") end
        return
    end

    local isCowork = (entry.kind == "cowork_stateless" or entry.kind == "cowork_stateful")

    if banner then banner.running(entry.label .. " - RUNNING") end

    -- Defer to the next loop tick so the running banner paints before the
    -- (possibly blocking-on-activate) work begins.
    hs.timer.doAfter(0, function()
        local ok, err = pcall(function()
            entry.run(function(delivered)
                if not banner then return end
                if isCowork then
                    -- Cowork: best we honestly know is that we sent it.
                    if delivered then
                        banner.done(entry.label .. " - DISPATCHED")
                    else
                        banner.fail(entry.label .. " - dispatch failed")
                    end
                else
                    if delivered then
                        banner.done(entry.label .. " - DONE")
                    else
                        banner.fail(entry.label .. " - FAILED")
                    end
                end
            end)
        end)
        if not ok and banner then
            banner.fail(entry.label .. " - error: " .. tostring(err))
        end
    end)
end

return M
