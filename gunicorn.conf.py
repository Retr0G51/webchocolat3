import os

# Servidor
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
workers = 1
worker_class = "sync"
timeout = 120  # Reducido de 300 a 120
keepalive = 5

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Proceso
preload_app = False  # Importante: no precargar la app
daemon = False
