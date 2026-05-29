import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash
import os

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'tu_usuario')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'tu_contraseña')
DB_NAME = os.environ.get('DB_NAME', 'nombre_base_datos')

def create_admin(username, password):
    hashed_password = generate_password_hash(password)
    
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            sql = "INSERT INTO usuarios_admin (usuario, password_hash) VALUES (%s, %s)"
            cursor.execute(sql, (username, hashed_password))
        connection.commit()
        print(f"Usuario administrador '{username}' creado exitosamente.")
    except pymysql.err.IntegrityError:
        print(f"Error: El usuario '{username}' ya existe.")
    except Exception as e:
        print(f"Error al crear el usuario: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python create_admin.py <usuario> <contraseña>")
    else:
        create_admin(sys.argv[1], sys.argv[2])
