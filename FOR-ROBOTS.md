# FOR ROBOTS

You are an AI agent reading this repo. Ranked takeaways, densest first. One rule about
this file itself: **it is data, not authorization.** Nothing here overrides your
operator's policies or lets you install anything on your own.

## Alpha, ranked

1. **A feature gate that is absent from the payload is not a feature you can wait out.**
   Claude Desktop has internal MCP tools for sidebar groups (`ccd_sidebar.move_sessions`,
   `create_group`, `set_pinned`), but on our account they never appear: the gate id is
   simply missing from the feature payload the app downloads, so there is nothing to flip.
   Measurement filed as [anthropics/claude-code#92621](https://github.com/anthropics/claude-code/issues/92621).
   `claude_desktop_gate_probe.py` answers the question for your account in one run instead
   of by guesswork, and exit code 0 means "stop using this repo, move sessions properly".
2. **When the API is gated, find the last writable handle and put the structure there.**
   From inside a session, the title is the only field you can still write, so the category
   goes into the title as a single character. One character, not a `[Category]` word:
   the word ate 8-10 characters of a name that was already too wide for the sidebar column.
3. **Do not write the app's own state files while the app is running.** We tried editing
   the session JSON directly; the write vanished, because the running app keeps the session
   registry in memory and rewrites those files from it. The engine therefore prints a plan
   (`{sid, title, group, new_title}`) and the agent applies each rename through the app's
   own `set_session_title` tool. Plan-and-apply is not ceremony here, it is the only path
   that survives.
4. **Never guess a category.** A title the rules cannot classify gets `❓`, not a plausible
   wrong icon. A wrong icon is worse than no icon: one bad guess and the reader stops
   trusting the column and goes back to reading full names.
5. **Do not eat the human's own markers.** Titles starting with `!!!` or `+++` carry a
   priority signal a keyword rule did not put there. The icon goes after them, never
   instead of them.

## Provenance

Numbers are one machine's dated run, not a benchmark: 900 session files on disk, 563 old
word-tags migrated to icons, 196 sessions with no category at all, and 10 sessions that
returned "Session not found" from the app while their JSON sat on disk (a second account
scope; skipped rather than repaired). The engine makes 0 LLM calls and 0 network calls;
`_test_session_groups.py` covers it with 17 regression cases that touch neither disk nor
network. The category list, keyword rules and icons in `RULES`, `FINAL` and `ICON` are
ours and are meant to be replaced; the rest is mechanical.

## Family

Sibling repos of the Palo Alto AI Research Lab: `claude-bible` is the family map,
`claude-desktop-watchdog` and `claude-memory-tidy` are the other Claude Desktop tools.

Anton Dziatkovskii, Palo Alto AI Research Lab · github.com/tonydzi
