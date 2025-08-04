#!/usr/bin/env python3
"""
Script para iniciar el servidor en modo desarrollo
"""
import uvicorn
import os
from dotenv import load_dotenv

def main():
    # Cargar variables de entorno
    load_dotenv()
    
    # Configuración del servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    print(f"🚀 Iniciando servidor en modo desarrollo...")
    print(f"📍 Host: {host}")
    print(f"🔌 Puerto: {port}")
    print(f"🔄 Reload: {reload}")
    print(f"📖 Documentación: http://{host}:{port}/")
    
    # Iniciar servidor
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    main() 