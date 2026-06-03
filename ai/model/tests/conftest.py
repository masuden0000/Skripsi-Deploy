import sys
import pathlib

# Tambahkan ai/model/ ke sys.path agar `model_ai` bisa diimpor saat pytest dijalankan dari mana saja
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
