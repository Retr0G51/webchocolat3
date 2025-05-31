#!/usr/bin/env python3
"""
WSGI Entry Point para Railway
"""
import os
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

logger = logging.getLogger(__name__)

try:
    logger.info("🚀 Iniciando aplicación WSGI...")
    
    # Importar la aplicación
    from app import app, setup_app
    
    logger.info("✅ Aplicación importada correctamente")
    
    # Configurar la aplicación
    setup_app()
    
    logger.info("✅ Aplicación configurada correctamente")
    
    # Verificar configuración
    logger.info(f"🔧 SECRET_KEY configurado: {'✅' if app.config.get('SECRET_KEY') else '❌'}")
    logger.info(f"🔧 DATABASE_URL configurado: {'✅' if os.environ.get('DATABASE_URL') else '❌'}")
    
    application = app
    
    logger.info("🌟 Aplicación WSGI lista")
    
except Exception as e:
    logger.error(f"❌ Error crítico en WSGI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    application.run()
