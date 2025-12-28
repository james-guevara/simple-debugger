#!/usr/bin/env python3
"""
Minimal terminal debugger using Textual + bdb.
A starting point for a nice, easy-to-use Python debugger.

Usage:
    python simple_debugger.py your_script.py
"""

import bdb
import sys
import linecache
from pathlib import Path
from threading import Thread
from queue import Queue

from textual.app import App, ComposeResult
from textual.widgets import Static, Header, Footer
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from rich.syntax import Syntax
from rich.text import Text


class DebuggerCore(bdb.Bdb):
    """Core debugger logic built on bdb."""

    def __init__(self, ui_queue: Queue, cmd_queue: Queue):
        super().__init__()
        self.ui_queue = ui_queue    # Send state to UI
        self.cmd_queue = cmd_queue  # Receive commands from UI
        self.current_frame = None

    def user_line(self, frame):
        """Called on every line execution."""
        self.current_frame = frame
        self._update_ui(frame)
        self._wait_for_command(frame)

    def user_exception(self, frame, exc_info):
        """Called when an exception occurs."""
        self.current_frame = frame
        self._update_ui(frame, exception=exc_info)
        self._wait_for_command(frame)

    def _update_ui(self, frame, exception=None):
        """Send current state to the UI."""
        state = {
            'filename': frame.f_code.co_filename,
            'lineno': frame.f_lineno,
            'function': frame.f_code.co_name,
            'locals': self._safe_repr_dict(frame.f_locals),
            'stack': self._get_stack_info(frame),
            'exception': str(exception[1]) if exception else None,
        }
        self.ui_queue.put(state)

    def _safe_repr_dict(self, d):
        """Safely convert locals dict to string reprs."""
        result = {}
        for k, v in d.items():
            if k.startswith('__'):
                continue
            try:
                result[k] = repr(v)[:100]  # Truncate long reprs
            except Exception:
                result[k] = '<error getting repr>'
        return result

    def _get_stack_info(self, frame):
        """Get stack frame info."""
        stack = []
        f = frame
        while f is not None:
            stack.append({
                'filename': Path(f.f_code.co_filename).name,
                'lineno': f.f_lineno,
                'function': f.f_code.co_name,
            })
            f = f.f_back
        return stack[:10]  # Limit depth

    def _wait_for_command(self, frame):
        """Wait for command from UI."""
        cmd = self.cmd_queue.get()

        if cmd == 'step':
            self.set_step()
        elif cmd == 'next':
            self.set_next(frame)
        elif cmd == 'continue':
            self.set_continue()
        elif cmd == 'quit':
            self.set_quit()


class CodeView(Static):
    """Displays source code with current line highlighted."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_file = None
        self.current_line = 0

    def update_code(self, filename: str, lineno: int):
        """Update the code display."""
        self.current_file = filename
        self.current_line = lineno

        # Read source lines
        try:
            with open(filename) as f:
                lines = f.readlines()
        except Exception:
            self.update("Could not read source file")
            return

        # Show context around current line
        start = max(0, lineno - 8)
        end = min(len(lines), lineno + 8)

        # Build display with line numbers
        display_lines = []
        for i in range(start, end):
            line_num = i + 1
            marker = "→ " if line_num == lineno else "  "
            display_lines.append(f"{marker}{line_num:4d} │ {lines[i].rstrip()}")

        code_text = "\n".join(display_lines)

        # Use Rich Syntax for highlighting
        syntax = Syntax(
            code_text,
            "python",
            theme="monokai",
            line_numbers=False,
        )
        self.update(syntax)


class VariablesView(Static):
    """Displays local variables."""

    def update_vars(self, locals_dict: dict):
        """Update variables display."""
        if not locals_dict:
            self.update("No local variables")
            return

        lines = []
        for name, value in locals_dict.items():
            lines.append(f"[cyan]{name}[/cyan] = {value}")

        self.update("\n".join(lines))


class StackView(Static):
    """Displays call stack."""

    def update_stack(self, stack: list):
        """Update stack display."""
        lines = []
        for i, frame in enumerate(stack):
            marker = "→ " if i == 0 else "  "
            lines.append(
                f"{marker}[yellow]{frame['function']}[/yellow] "
                f"({frame['filename']}:{frame['lineno']})"
            )

        self.update("\n".join(lines))


class StatusBar(Static):
    """Shows current execution status."""

    def update_status(self, filename: str, lineno: int, function: str, exception: str = None):
        if exception:
            self.update(f"[red]Exception: {exception}[/red]")
        else:
            self.update(f"[green]●[/green] {Path(filename).name}:{lineno} in [yellow]{function}[/yellow]")


class DebuggerApp(App):
    """Main debugger application."""

    CSS = """
    #code-view {
        height: 60%;
        border: solid green;
        padding: 1;
    }

    #bottom-pane {
        height: 40%;
    }

    #variables {
        width: 50%;
        border: solid blue;
        padding: 1;
    }

    #stack {
        width: 50%;
        border: solid magenta;
        padding: 1;
    }

    #status {
        dock: bottom;
        height: 1;
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("s", "step", "Step Into"),
        Binding("n", "next", "Step Over"),
        Binding("c", "continue", "Continue"),
        Binding("q", "quit_debugger", "Quit"),
    ]

    def __init__(self, ui_queue: Queue, cmd_queue: Queue):
        super().__init__()
        self.ui_queue = ui_queue
        self.cmd_queue = cmd_queue

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield CodeView(id="code-view")
        with Horizontal(id="bottom-pane"):
            yield VariablesView(id="variables")
            yield StackView(id="stack")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self):
        """Start checking for debugger updates."""
        self.set_interval(0.05, self.check_updates)

    def check_updates(self):
        """Check for state updates from debugger."""
        try:
            while not self.ui_queue.empty():
                state = self.ui_queue.get_nowait()
                self.update_display(state)
        except Exception:
            pass

    def update_display(self, state: dict):
        """Update all UI components with new state."""
        self.query_one("#code-view", CodeView).update_code(
            state['filename'], state['lineno']
        )
        self.query_one("#variables", VariablesView).update_vars(state['locals'])
        self.query_one("#stack", StackView).update_stack(state['stack'])
        self.query_one("#status", StatusBar).update_status(
            state['filename'], state['lineno'], state['function'], state['exception']
        )

    def action_step(self):
        self.cmd_queue.put('step')

    def action_next(self):
        self.cmd_queue.put('next')

    def action_continue(self):
        self.cmd_queue.put('continue')

    def action_quit_debugger(self):
        self.cmd_queue.put('quit')
        self.exit()


def run_debugger(script_path: str):
    """Run the debugger on a script."""
    ui_queue = Queue()
    cmd_queue = Queue()

    debugger = DebuggerCore(ui_queue, cmd_queue)
    app = DebuggerApp(ui_queue, cmd_queue)

    def run_script():
        """Run the target script under debugger control."""
        try:
            with open(script_path) as f:
                code = compile(f.read(), script_path, 'exec')

            # Set up globals for the script
            script_globals = {
                '__name__': '__main__',
                '__file__': script_path,
                '__builtins__': __builtins__,
            }

            debugger.run(code, script_globals)
        except bdb.BdbQuit:
            pass
        except Exception as e:
            ui_queue.put({
                'filename': script_path,
                'lineno': 0,
                'function': '<module>',
                'locals': {},
                'stack': [],
                'exception': str(e),
            })

    # Run script in background thread
    script_thread = Thread(target=run_script, daemon=True)
    script_thread.start()

    # Run the UI (blocking)
    app.run()


def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_debugger.py <script.py>")
        print("\nControls:")
        print("  s - Step into")
        print("  n - Step over (next)")
        print("  c - Continue")
        print("  q - Quit")
        sys.exit(1)

    script_path = sys.argv[1]
    if not Path(script_path).exists():
        print(f"Error: {script_path} not found")
        sys.exit(1)

    run_debugger(script_path)


if __name__ == "__main__":
    main()
