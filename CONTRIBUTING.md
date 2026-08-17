# Contributing

Contributions are welcome.

## Development

Run the dashboard from source on Windows:

```bat
RUN_SOURCE.bat
```

or:

```powershell
py app\server.py
```

The application uses the Python standard library at runtime.

## Before opening a pull request

Run:

```powershell
py -m pip install -r requirements-build.txt
py -m bandit -q -r app
py -m py_compile app\server.py
```

Please keep these properties intact unless a change explicitly requires
otherwise:

- HTTP server binds to `127.0.0.1`;
- filesystem access remains scoped to the configured `.runelite` root;
- raid logs/screenshots are not uploaded;
- source RuneLite files are not modified;
- user configuration remains under `%LOCALAPPDATA%`.

For security-sensitive changes, explain the threat model and why the change
does not broaden access unexpectedly.
