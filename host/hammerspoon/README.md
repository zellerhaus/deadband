# Deadband Cowork Console — Hammerspoon host

The Mac-side receiver for the `cowork_console` firmware.

The panel is a USB HID device. It emits collision-proof key chords; this
Hammerspoon configuration binds the exact same chords and does the work —
toggling Focus, switching audio devices, muting the mic, drawing on-screen
banners, and dispatching Claude Cowork jobs. Media keys and the screen lock
never touch Hammerspoon; the panel sends those natively.

The split is deliberate. The panel stays a clean HID device that degrades
gracefully when Hammerspoon is off — media, volume, and lock still work — and
the integration lives on your machine, in code you own.

---

## What runs where

| Action | Where it runs |
|---|---|
| Volume, scrub, play/pause (encoder) | Native HID — macOS, no Hammerspoon |
| Screen lock (button long-press) | Native HID — macOS, no Hammerspoon |
| Focus / DND (toggle 1) | Hammerspoon → Shortcuts CLI |
| Audio output switch (toggle 2) | Hammerspoon → `hs.audiodevice` |
| Mic mute (rocker) | Hammerspoon → `hs.audiodevice` |
| Launcher arm + dispatch (rotary + button tap) | Hammerspoon |

---

## Prerequisites

**On the Mac:**

- **[Hammerspoon](https://www.hammerspoon.org/).** `brew install hammerspoon`,
  then launch it once and grant **Accessibility** permission when prompted.
  This is not optional — Hammerspoon needs Accessibility to send keystrokes to
  other apps (used to drive the Claude Desktop composer for Cowork jobs).
- **Claude Desktop** (`/Applications/Claude.app`). The dispatcher targets the
  app by the process name `Claude`. Cowork jobs are driven through its UI; see
  [Known limitations](#known-limitations).
- **Shortcuts CLI** (`/usr/bin/shortcuts`, ships with macOS) — used for Focus /
  DND toggling. You must create two Shortcuts yourself; see
  [Focus / DND setup](#focus--dnd-setup).
- **SwitchAudioSource** — *only if you prefer it over the built-in
  `hs.audiodevice` path.* The shipped `audio.lua` uses `hs.audiodevice` and does
  not require it. Install with `brew install switchaudio-osx` if you decide to
  swap the implementation.

**On the panel:**

- `cowork_console.py` flashed as `code.py`.
- `adafruit_hid` in `/CIRCUITPY/lib/`. Install with circup:

  ```sh
  circup install adafruit_hid
  ```

---

## Install

The Hammerspoon config lives in `host/hammerspoon/deadband/`. Get it into your
`~/.hammerspoon/` directory and require it from your `init.lua`.

**1. Link (or copy) the module into place.** A symlink keeps it tracking the
repo:

```sh
ln -s "$(pwd)/host/hammerspoon/deadband" ~/.hammerspoon/deadband
```

Run that from the firmware repo root. To copy instead of link:

```sh
cp -R host/hammerspoon/deadband ~/.hammerspoon/deadband
```

**2. Require it from `~/.hammerspoon/init.lua`.** Add one line:

```lua
require("deadband.init")
```

If you already have an `init.lua`, append the line. If not, that one line is the
whole file.

**3. Reload.** Open the Hammerspoon menu-bar icon → **Reload Config**, or run
`hs.reload()` in the Hammerspoon console. The first reload after granting
Accessibility may need a second reload to take effect.

**4. Verify.** Turn the rotary one position. A banner should appear naming the
launcher and prompting `Press Launch to initiate`. If it does, the host is
listening.

---

## Configuration

Open `~/.hammerspoon/deadband/init.lua`. The top-of-file config block holds the
device names and paths you may need to change:

```lua
-- Audio device names — must match System Settings → Sound exactly.
local OUTPUT_PRIMARY   = "External Headphones"
local OUTPUT_SECONDARY = "Shure MV7"
```

Find your exact device names with:

```sh
# Built-in, no install required:
hs.audiodevice.allOutputDevices()   -- run in the Hammerspoon console
```

Match the strings character-for-character, including capitalization. The audio
device names also have a copy at the top of `deadband/audio.lua`; the `init.lua`
block is the one you edit.

Launcher targets (Gmail compose URL, Desktop/Downloads paths, Cowork prompts)
live in `deadband/dispatch.lua`. Edit them there.

---

## Chord map

The firmware sends these. Hammerspoon binds these. One table, documented once.

**Hyper** = `Command + Control + Option + Shift` held together with the key.
There is no single Hyper key on the hardware — it is built from the four
modifiers on both ends.

### Rotary — launcher select (Hyper + key)

Turning the rotary arms a launcher; it does not run it. The button tap runs the
armed one.

| Position | Chord | Default launcher |
|---|---|---|
| 1  | Hyper + `1` | GMAIL — open Gmail compose |
| 2  | Hyper + `2` | NEW CHAT — Claude Desktop, new chat (⌘N) |
| 3  | Hyper + `3` | MORNING BRIEF — Cowork (stateful) |
| 4  | Hyper + `4` | TIDY DESKTOP — Cowork (stateless, `~/Desktop`) |
| 5  | Hyper + `5` | TIDY DOWNLOADS — Cowork (stateless, `~/Downloads`) |
| 6  | Hyper + `6` | PSALMLOG DAILY UPDATE — Cowork (stateful) |
| 7  | Hyper + `7` | Reserved — Cowork slot |
| 8  | Hyper + `8` | Reserved — Cowork slot |
| 9  | Hyper + `9` | Reserved — Cowork slot |
| 10 | Hyper + `0` | Reserved — Cowork slot |
| 11 | Hyper + `-` | Reserved — Cowork slot |
| 12 | Hyper + `=` | Reserved — Cowork slot |

### Toggles, rocker, button

| Gesture | Chord | Bound action |
|---|---|---|
| Toggle 1 ON  | Hyper + `F13` | DND on |
| Toggle 1 OFF | Hyper + `F14` | DND off |
| Toggle 2 ON  | Hyper + `F15` | Audio output → secondary (Shure MV7) |
| Toggle 2 OFF | Hyper + `F16` | Audio output → primary (External Headphones) |
| Rocker ON    | Hyper + `F17` | Mic muted |
| Rocker OFF   | Hyper + `F18` | Mic unmuted |
| Button tap   | Hyper + `Space` | Run the armed launcher |
| Button long-press | *(native)* | Lock screen — `Command + Control + Q`, sent by the panel. **Not bound by Hammerspoon.** |

The long-press lock is sent natively by the firmware and never reaches
Hammerspoon. Do not bind `Command + Control + Q` here.

---

## Focus / DND setup

The Shortcuts CLI cannot toggle a Focus mode directly; it runs named Shortcuts.
Create two, exactly named:

- **`Deadband DND On`** — one action: *Set Focus* → *Do Not Disturb* → *On*.
- **`Deadband DND Off`** — one action: *Set Focus* → *Do Not Disturb* → *Off*.

`audio.lua` invokes them as `shortcuts run "Deadband DND On"` /
`shortcuts run "Deadband DND Off"`. If the Shortcuts CLI is unavailable, DND is
skipped and logged — the rest of the toggle bindings still work. See
[Known limitations](#known-limitations) for why DND is best-effort.

---

## Known limitations

**One-way HID — the panel cannot hear the Mac.** The connection is the panel
talking to the host, never the reverse. The host cannot report success back to
the panel, so the button LED cannot reflect whether a job actually ran. The LED
gives *local* feedback only: a five-pulse blink on dispatch means the tap was
sent, not that the work finished. Success and failure are reported on screen by
the Hammerspoon **banner**, which is the source of truth for outcome. If you
need to know a Cowork job ran, watch the banner, not the LED.

**DND control and reconcile are best-effort.** DND is driven through the
Shortcuts CLI, which fires the toggle but does not return reliable state. There
is no robust way to read current Focus state back, so the host cannot
authoritatively reconcile DND against external changes (e.g. you toggle Focus
from Control Center). Audio output and mic mute *do* reconcile — an
`hs.audiodevice.watcher` re-asserts the last-known toggle position on external
drift — but DND does not participate in that loop. Treat the toggle as a
command, not a guaranteed lock.

**Cowork has no trigger API — it is UI automation only.** There is no supported
programmatic way to start a named Cowork job today. Specifically:

- The `claude` CLI (v2.1.96 at `/opt/homebrew/bin/claude`) is **Claude Code
  only**. `claude cowork` is not a command — it just re-prints top-level help,
  and `claude --help | grep -i cowork` returns nothing.
- Claude Desktop registers the `claude://` URL scheme, but the only deep links
  it handles are `claude://claude.ai/mcp-auth-callback/sdk` (auth) and
  `claude://cowork/shared-artifact?uuid=<uuid>` (which opens an *existing shared
  artifact* — not a job launcher). There is no
  `claude://cowork/new|start|run|task|resume` route in the app bundle.

Because no CLI subcommand and no usable URL scheme exist, the dispatcher drives
the desktop UI. The approach:

1. **Focus the app:**
   `osascript -e 'tell application "Claude" to activate'`
   The app is **not** AppleScript-scriptable (no `.sdef`), so everything goes
   through System Events / GUI keystrokes — never app-specific verbs.

2. **Paste the prompt** (clipboard paste is far more reliable than `keystroke`
   for long or multiline prompts):

   ```sh
   osascript -e 'set the clipboard to "<PROMPT TEXT>"'
   osascript -e 'tell application "System Events" to tell process "Claude" to keystroke "v" using command down'
   ```

3. **Submit** with Return:
   `osascript -e 'tell application "System Events" to tell process "Claude" to key code 36'`

Two caveats the host has to live with:

- Hammerspoon must hold **Accessibility** permission to send System Events
  keystrokes to Claude. Without it, dispatch silently fails. Grant it under
  System Settings → Privacy & Security → Accessibility.
- Reaching a **specific named** Cowork task has no programmatic selector. The
  reliable pattern is: focus the app, optionally click into the Cowork task
  list, then paste + Return into the active composer. Stateful jobs
  (MORNING BRIEF, PSALMLOG DAILY UPDATE) assume the right task is the active
  one. If the wrong context is foregrounded, the prompt lands in the wrong
  place. This is a known constraint of the UI-automation path, not a bug.

If a Cowork trigger API ships later, the dispatcher's `run` functions are the
only thing that needs to change — the chord contract and bindings stay put.
