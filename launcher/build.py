import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
here = os.path.dirname(os.path.abspath(__file__))

print("Installing dependencies...")
subprocess.run(
    [sys.executable, "-m", "pip", "install",
     "pyinstaller", "customtkinter", "requests", "pillow"],
    check=True
)

print("\nBuilding launcher.exe...")
subprocess.run(
    [sys.executable, "-m", "PyInstaller",
     "--onefile",
     "--windowed",
     "--name", "UltimateShowdown Launcher",
     "--icon", "icon.ico",
     "--add-data", "icon.ico;.",
     "--distpath", os.path.join(here, "dist"),
     "--workpath", os.path.join(here, "build_tmp"),
     "--specpath", here,
     "launcher.py"],
    check=True
)

print("\nDone! Your exe is at:")
print(os.path.join(here, "dist", "UltimateShowdown Launcher.exe"))
input("\nPress Enter to exit...")
