import os
import io
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, flash
import pymysql
import pymysql.cursors
from werkzeug.security import check_password_hash
import openpyxl

app = Flask(__name__)
# ¡IMPORTANTE! Cambia esto por una clave secreta fuerte y aleatoria en producción
app.secret_key = os.environ.get('SECRET_KEY', 'una_clave_secreta_muy_segura_para_desarrollo')

# Configuración de la base de datos
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

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

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

# --- RUTAS ADMINISTRATIVAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "SELECT id, password_hash FROM usuarios_admin WHERE usuario = %s"
                cursor.execute(sql, (usuario,))
                admin = cursor.fetchone()
                
            if admin and check_password_hash(admin['password_hash'], password):
                session['admin_logged_in'] = True
                session['admin_user'] = usuario
                return redirect(url_for('dashboard'))
            else:
                flash('Credenciales incorrectas.', 'error')
        except Exception as e:
            flash(f'Error de conexión a la base de datos: {str(e)}', 'error')
        finally:
            if 'connection' in locals() and connection.open:
                connection.close()
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def dashboard():
    registros = []
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM registros_tiempo ORDER BY marca_de_tiempo DESC"
            cursor.execute(sql)
            registros = cursor.fetchall()
    except Exception as e:
        flash(f'Error al cargar registros: {str(e)}', 'error')
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
            
    return render_template('dashboard.html', registros=registros)

@app.route('/admin/exportar')
@login_required
def exportar():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM registros_tiempo ORDER BY marca_de_tiempo DESC"
            cursor.execute(sql)
            registros = cursor.fetchall()
            
        # Crear archivo Excel en memoria usando openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Registros"
        
        # Escribir encabezados
        headers = ["ID", "Nombre Técnico", "Tipo Registro", "Latitud", "Longitud", "Precisión GPS", "Marca de Tiempo"]
        ws.append(headers)
        
        # Escribir datos
        for r in registros:
            # Eliminar timezone info si hay problemas (MariaDB timestamp returns as datetime)
            fecha = r['marca_de_tiempo'].replace(tzinfo=None) if hasattr(r['marca_de_tiempo'], 'tzinfo') else r['marca_de_tiempo']
            ws.append([
                r['id'], 
                r['nombre_tecnico'], 
                r['tipo_registro'], 
                float(r['latitud']), 
                float(r['longitud']), 
                float(r['precision_gps']), 
                fecha
            ])
            
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name="registros_asistencia.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        return f"Error al exportar: {str(e)}", 500
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
