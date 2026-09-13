# claude-session-icons

Put a one-character category icon at the front of every Claude Desktop session title, so a sidebar of 900 sessions becomes readable at a glance.

```
⚙️ Nightly debt sweeper
💰 Article: control-plane casebook
🔬 DR fan-out 2026-08-28
🧠 Root cause: memory index loses lines
❓ 3D game
```

## Why this exists

Claude Desktop ships sidebar groups, and the app has internal MCP tools to move sessions between them (`ccd_sidebar.move_sessions`, `create_group`, `set_pinned`). On our account those tools never appear: they sit behind a server feature gate that is simply absent from the feature payload the app downloads. We filed [anthropics/claude-code#92621](https://github.com/anthropics/claude-code/issues/92621) with the measurement.

Until the gate opens, the only writable handle on a session from inside a session is its **title**. So the category lives there, as an icon. One character instead of a `[Category]` word that ate 8-10 characters of a name that was already too long for the sidebar column.

If the gate ever opens for you, `claude_desktop_gate_probe.py` says so with exit code 0, and you should move sessions properly instead of using this.

## What is in here

| file | what it does |
|---|---|
| `session_groups.py` | the engine, 0 LLM calls, 0 network. Reads the app's own session files, guesses a category from the title by keyword rules, and prints a rename plan as JSON |
| `_test_session_groups.py` | 17 regression cases, no network, no disk |
| `claude_desktop_gate_probe.py` | reads the app's cached feature payload and reports whether a given gate id is ON, OFF or absent |
| `SKILL.md` | the agent-facing skill: when to tag, how to batch renames, where the boundaries are |

## Usage

```bash
python session_groups.py groups                 # the icon alphabet
python session_groups.py plan  --limit 60       # sessions with no icon yet -> JSON plan
python session_groups.py retag --limit 100 --all  # migrate old [Word] tags -> icons
python session_groups.py table --limit 500      # CSV of everything, for a spreadsheet review
```

The engine in `session_groups.py` never renames anything itself. It prints `{sid, title, group, new_title}` and the agent applies each one with the app's own `set_session_title` MCP tool. That split is deliberate: a script that edits the app's JSON files directly does not work, because the running app keeps the session registry in memory and rewrites those files from it. We tried; the write vanished.

## Adapt before you run it

The category list, the keyword rules and the icons are ours. Yours will differ. Everything you need to change is at the top of `session_groups.py`: `RULES`, `FINAL`, `ICON`. The rest is mechanical.

Two behaviours worth keeping:

- **Never guess.** A title the rules cannot classify gets `❓`, not a plausible-looking wrong icon. A wrong icon is worse than no icon, because you stop reading the name.
- **Do not eat the user's own markers.** Titles starting with `!!!` or `+++` carry a human priority signal. The icon goes after them, not instead of them.

## Where it runs

Windows, macOS and Linux paths are handled; `CLAUDE_DESKTOP_DIR` overrides. Built for one person's fleet of six machines, so expect fleet-shaped assumptions in `SKILL.md`. The engine itself has none.

## Measurement, not a claim

On the machine this was built for, measured 2026-09-10: 900 session files on disk, 563 old word-tags migrated to icons, 196 sessions that had no category at all. Ten sessions returned "Session not found" from the app while their JSON sat on disk; those live in a second account scope and are skipped rather than repaired.

Licensed MIT, see [LICENSE](LICENSE); if you cite this work, use the metadata in [CITATION.cff](CITATION.cff).
