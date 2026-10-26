# EscApp-Games

What particular games need to run well in [EscApp](https://github.com/Zig1375/EscApp): launch settings, what goes
into their bottle, and small edits to their settings files. EscApp downloads this repository's index once a day,
finds the player's games in it on the Mac and applies what it says, so a fix for a game reaches every player
without a new app release.

The design is in EscApp's `docs/GAME-MODULES.md`.

## Data only

A module is data. Every action it can ask for is one EscApp implements from a closed list; a module can't run
anything. Never accepted here, whatever the license or the intent:

- executables and libraries (`.exe`, `.dll`, `.asi`, `.dylib`, `.so`, or any file with a PE or Mach-O header);
- scripts a game or the system would run (`.lua`, `.py`, `.js`, `.bat`, `.cmd`, `.ps1`, `.sh`, `.vbs`…);
- cracks, DRM or anti-cheat bypasses, cheats, trainers;
- modified game files that may not be redistributed.

A fix that needs code belongs in EscApp's Wine build ([EscApp-Runtime](https://github.com/Zig1375/EscApp-Runtime)).

## Layout

- `modules/` — one file per game, named by its slug (`banished.json`). One module covers the game in every store.
- `shared/` — modules many games depend on (`cjk-fonts.json`, `unreal-4.json`), or that apply by engine.
- `files/<slug>/` — files the `files` action adds next to a game (configs, never code), each with its license in
  the module's `credits`.
- `games.json` — the index EscApp reads, built and committed by CI. Don't edit it by hand.

## Checking modules

`schema/module.schema.json` (files in `modules/`) and `schema/shared.schema.json` (files in `shared/`) describe the
format; put `"$schema": "../schema/module.schema.json"` at the top of a module and an editor checks it as you type.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t .
```

## Privacy

EscApp downloads the whole index and matches games on the Mac, so nobody learns which games a player has. Only a
file from `files/` is fetched one at a time, for the game that needs it, pinned by SHA-256 in the index.

## License

Apache-2.0. Files in `files/` carry the license named in their module's `credits`.
