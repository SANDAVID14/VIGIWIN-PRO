"""
Lanzador directo de VIGI-WIN PRO v1.0
Ejecutar con: python run_app.py
"""
import sys
import os

# Asegurar que el directorio raíz está en sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from vigiwin.main import main

if __name__ == "__main__":
    main()
