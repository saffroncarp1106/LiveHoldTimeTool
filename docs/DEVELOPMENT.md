# Development

## Repository layout

```text
LiveHoldTimeTool/
├── README.md              Original project description and usage
├── requirements.txt       Python runtime dependencies
├── src/
│   └── holdtimes.py        Application source (version 0.1.2)
└── docs/
    └── DEVELOPMENT.md     Source setup and build instructions
```

## Run from source on Windows

Install Python with pip, then open PowerShell in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\holdtimes.py
```

The application writes `settings.ini` in the current working directory.
Run it from the repository root to keep those settings in a consistent location.
Local settings and Python environments are excluded from Git.

## Build a Windows executable

With the runtime dependencies installed in the environment above:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --specpath build --name HoldTimes src\holdtimes.py
```

The executable is written to `dist\HoldTimes.exe`. Place it in its own folder
when distributing it so it can create its settings file. Build outputs are
excluded from Git. Verify the executable on the target Windows system before
distributing it.
