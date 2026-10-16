"""Entry point for MicHP.exe (PyInstaller). Also runnable with: python michp_app.py"""
import sys

from michp_pc.app import main

if __name__ == "__main__":
    sys.exit(main())
