# Simple Debugger

A minimal, visual terminal debugger for Python built with Textual.

## Project Goals

- Clean, pleasant terminal UI for debugging Python code
- Easy to use with minimal learning curve
- Built on Python's `bdb` module + Textual for the UI

## Future Features to Consider

- Breakpoints panel (toggle with keybinding)
- Watch expressions
- Omniscient/replay debugging (record execution, browse history)
- Checkpointing for long-running scripts
- Better variable inspection (expandable dicts/lists)

## References

- [Textual](https://github.com/Textualize/textual) - TUI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [pudb](https://github.com/inducer/pudb) - Existing visual debugger (for inspiration)
- [cyberbrain](https://github.com/laike9m/Cyberbrain) - Omniscient debugging approach
- [time-traveling-debugger](https://github.com/airportyh/time-traveling-debugger) - Replay debugging

## Setup

```bash
source .venv/bin/activate
python simple_debugger.py <script.py>
```

## Controls

- `s` - Step into
- `n` - Step over
- `c` - Continue
- `q` - Quit
