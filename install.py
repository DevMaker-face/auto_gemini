#!/usr/bin/env python3
"""
Script de instalación para el Asistente IA Autónomo
===================================================

Este script ayuda a configurar el entorno necesario para ejecutar el asistente.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# FIX: Forzar la codificación UTF-8 para la salida en consolas Windows (soluciona UnicodeEncodeError)
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        # Si falla (ej. en un entorno sin buffer), ignorar y usar la configuración por defecto
        pass

def check_python_version():
    """Verifica la versión de Python"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 o superior es requerido")
        print(f"Versión actual: {sys.version}")
        sys.exit(1)
    print("✅ Python version compatible")

def install_dependencies():
    """Instala las dependencias necesarias"""
    print("\n📦 Instalando dependencias...")
    
    # Intentar instalar dependencias principales
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencias instaladas correctamente")
    except subprocess.CalledProcessError as e:
        print("❌ Error instalando dependencias:")
        print(e.stderr.decode())
        return False
    
    return True

def setup_directories():
    """Crea los directorios necesarios"""
    print("\n📁 Configurando directorios...")
    
    directories = [
        "agent_tools",
        "desarrollos", 
        "agent_memory"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directorio creado: {directory}")

def create_sample_keys_file():
    """Crea un archivo de ejemplo para las API keys"""
    keys_file = Path("keys.json")
    
    if not keys_file.exists():
        print("\n🔑 Creando archivo de ejemplo para API keys...")
        
        sample_keys = {
            "gemini_api_keys": [
                "TU_API_KEY_AQUI"
            ],
            "notas": "Obtén tu API key de Gemini en: https://makersuite.google.com/app/apikey"
        }
        
        with open(keys_file, 'w') as f:
            json.dump(sample_keys, f, indent=2)
        
        print("✅ Archivo keys.json creado")
        print("⚠️  Recuerda agregar tu API key real antes de usar Gemini")
    else:
        print("✅ Archivo keys.json ya existe")

def check_ollama():
    """Verifica si Ollama está instalado y disponible"""
    print("\n🦙 Verificando Ollama...")
    
    try:
        result = subprocess.run(["ollama", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama encontrado: {result.stdout.strip()}")
            
            # Verificar modelos disponibles
            try:
                models_result = subprocess.run(["ollama", "list"], 
                                             capture_output=True, text=True)
                if models_result.returncode == 0:
                    print("📋 Modelos disponibles:")
                    print(models_result.stdout)
                else:
                    print("⚠️ No se pudieron listar los modelos")
            except:
                print("⚠️ Error verificando modelos")
                
        else:
            print("❌ Ollama no está instalado o no está en el PATH")
            print("   Instala Ollama desde: https://ollama.com")
            
    except FileNotFoundError:
        print("❌ Ollama no está instalado")
        print("   Instala Ollama desde: https://ollama.com")
        print("   O ejecuta: curl -fsSL https://ollama.com/install.sh | sh")

def create_startup_script():
    """Crea un script de inicio para facilitar el uso"""
    print("\n🚀 Creando script de inicio...")
    
    # Script para Unix/Linux/Mac
    startup_script_unix = """#!/bin/bash
cd "$(dirname "$0")"
python3 main_mejorado.py "$@"
"""
    
    # Script para Windows
    startup_script_windows = """@echo off
cd /d "%~dp0"
python main_mejorado.py %*
"""
    
    # Crear script para Unix
    with open("start.sh", "w") as f:
        f.write(startup_script_unix)
    os.chmod("start.sh", 0o755)
    
    # Crear script para Windows
    with open("start.bat", "w") as f:
        f.write(startup_script_windows)
    
    print("✅ Scripts de inicio creados: start.sh y start.bat")

def main():
    """Función principal del instalador"""
    print("🤖 Instalador del Asistente IA Autónomo")
    print("=" * 50)
    
    # Verificaciones
    check_python_version()
    
    # Instalación
    if not install_dependencies():
        print("\n❌ Falló la instalación de dependencias")
        print("Por favor, instala manualmente con: pip install -r requirements.txt")
        return
    
    setup_directories()
    create_sample_keys_file()
    check_ollama()
    create_startup_script()
    
    print("\n" + "=" * 50)
    print("🎉 Instalación completada!")
    print("\nPróximos pasos:")
    print("1. Edita keys.json y agrega tu API key de Gemini (opcional)")
    print("2. Asegúrate de que Ollama esté ejecutándose")
    print("3. Ejecuta el asistente con:")
    print("   - Linux/Mac: ./start.sh")
    print("   - Windows: start.bat")
    print("   - Directo: python main_mejorado.py")
    print("\n¡Disfruta tu asistente IA autónomo! 🤖✨")

if __name__ == "__main__":
    main()
