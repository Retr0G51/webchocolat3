"""
WSGI Entry Point para Railway
"""
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting WSGI application...")

# Importar la aplicación Flask
from app import app

# La aplicación Flask se exporta como 'application' para Gunicorn
application = app

logger.info("WSGI application ready")

if __name__ == "__main__":
    application.run()
