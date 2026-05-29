import sys
import os

# Ajusta esta ruta al directorio raíz de tu aplicación en DirectAdmin
# En DirectAdmin usando Python Selector, esto a menudo se configura automáticamente.
# Si necesitas un entorno virtual específico, podrías tener que apuntar al ejecutable python del venv:
# INTERP = os.path.expanduser("/home/tu_usuario/virtualenv/ruta_app/3.8/bin/python")
# if sys.executable != INTERP:
#     os.execl(INTERP, INTERP, *sys.argv)

# Añade el directorio actual al path de Python para que pueda encontrar app.py
sys.path.insert(0, os.path.dirname(__file__))

# Importa el objeto Flask ('app') desde tu archivo app.py 
# y renómbralo a 'application' (requerido por Passenger)
from app import app as application
