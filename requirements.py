import importlib.util
import subprocess
import sys

# Lista de bibliotecas necessarias
required_packages = [
    "streamlit",
    "pandas",
    "numpy"
]

def is_installed(package):
    return importlib.util.find_spec(package) is not None

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# instala somente se ainda não esta instalado
if __name__ == "__main__":
    for package in required_packages:
        if not is_installed(package):
            print(f"📦 Instalando {package}...")
            install(package)
        else:
            print(f"✅ {package} já está instalado.")
