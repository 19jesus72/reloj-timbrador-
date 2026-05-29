import os
from flask import Flask, render_template, request, jsonify
import pymysql
import pymysql.cursors

app = Flask(__name__)

# Configuración de la base de datos (deberías usar variables de entorno en producción)
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'tu_usuario')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'tu_contraseña')
DB_NAME = os.environ.get('DB_NAME', 'nombre_base_datos')

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/registrar', methods=['POST'])
def registrar_asistencia():
    data = request.get_json()
    
    nombre_tecnico = data.get('nombre_tecnico')
    tipo_registro = data.get('tipo_registro')
    latitud = data.get('latitud')
    longitud = data.get('longitud')
    precision_gps = data.get('precision_gps')
    
    # Validación básica de datos
    if not all([nombre_tecnico, tipo_registro, latitud is not None, longitud is not None, precision_gps is not None]):
        return jsonify({"error": "Faltan datos requeridos"}), 400
        
    if tipo_registro not in ['Entrada', 'Salida']:
        return jsonify({"error": "Tipo de registro inválido"}), 400
        
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO registros_tiempo 
                (nombre_tecnico, tipo_registro, latitud, longitud, precision_gps)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (nombre_tecnico, tipo_registro, latitud, longitud, precision_gps))
        connection.commit()
    except Exception as e:
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
            
    return jsonify({"mensaje": f"Registro de {tipo_registro} guardado exitosamente."}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
