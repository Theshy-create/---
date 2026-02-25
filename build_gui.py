import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ico = "app.ico" if os.path.exists("app.ico") else ""
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--onedir", "--windowed",
    "--name", "AegisVault",
    "--hidden-import", "PyQt6.sip",
    "--hidden-import", "PyQt6.QtWidgets",
    "--hidden-import", "PyQt6.QtCore",
    "--hidden-import", "PyQt6.QtGui",
    "--collect-submodules", "PyQt6",
    "--add-data", "db.py;.",
    "main_gui.py",
]
if ico:
    cmd.insert(cmd.index("--hidden-import"), "--icon")
    cmd.insert(cmd.index("--hidden-import"), ico)
print("Building...")
subprocess.run(cmd, check=True)
print("\nDone! exe in dist/AegisVault/")
