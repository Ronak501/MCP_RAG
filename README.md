# Flask Code Dashboard

This repository now exposes a Flask app that helps you browse the codebase and inspect evaluation logs visually.

## Run

```powershell
.\.venv\Scripts\python.exe app.py
```

## Views

- `/` - code structure, file list, file type summary, and log summaries
- `/file/<path>` - view a source file with line numbers
- `/logs` - view log summaries and recent log previews

## Notes

- The surveillance-specific packages and scripts were removed.
- The dashboard is read-only and does not modify files or logs.
