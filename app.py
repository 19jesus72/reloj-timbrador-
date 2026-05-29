import os
import io
import logging
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, flash
import pymysql
import pymysql.cursors
from werkzeug.security import check_password_hash
import openpyxl

# Configuración de logs de eventos
logging.basicConfig(
    filename='app_eventos.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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

def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def tecnico_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'tecnico_logged_in' not in session:
            return redirect(url_for('login_tecnico'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE TÉCNICOS ---

@app.route('/login_tecnico', methods=['GET', 'POST'])
def login_tecnico():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                sql = "SELECT id, password_hash, nombre_completo FROM tecnicos WHERE usuario = %s"
                cursor.execute(sql, (usuario,))
                tecnico = cursor.fetchone()
            if tecnico and check_password_hash(tecnico['password_hash'], password):
                session['tecnico_logged_in'] = True
                session['tecnico_id'] = tecnico['id']
                session['tecnico_nombre'] = tecnico['nombre_completo']
                logging.info(f"Técnico inició sesión: {tecnico['nombre_completo']} ({usuario})")
                return redirect(url_for('index'))
            else:
                flash('Credenciales incorrectas.', 'error')
        except Exception as e:
            logging.error(f"Error BD login_tecnico: {str(e)}")
            flash('Error de conexión a la base de datos.', 'error')
        finally:
            if 'connection' in locals() and connection.open:
                connection.close()
    return render_template('login_tecnico.html')

@app.route('/logout_tecnico')
def logout_tecnico():
    nombre = session.get('tecnico_nombre', 'Desconocido')
    session.pop('tecnico_logged_in', None)
    session.pop('tecnico_id', None)
    session.pop('tecnico_nombre', None)
    logging.info(f"Técnico cerró sesión: {nombre}")
    return redirect(url_for('login_tecnico'))

@app.route('/')
@tecnico_login_required
def index():
    return render_template('index.html')

@app.route('/api/registrar', methods=['POST'])
@tecnico_login_required
def registrar_asistencia():
    data = request.get_json()
    
    nombre_tecnico = session.get('tecnico_nombre')
    tipo_registro = data.get('tipo_registro')
    latitud = data.get('latitud')
    longitud = data.get('longitud')
    precision_gps = data.get('precision_gps')
    ingeniero_a_cargo = data.get('ingeniero_a_cargo')
    actividades_diarias = data.get('actividades_diarias', '')
    
    if not all([tipo_registro, latitud is not None, longitud is not None, precision_gps is not None, ingeniero_a_cargo]):
        logging.error(f"Error de datos para {nombre_tecnico}. Faltan campos requeridos.")
        return jsonify({"error": "Faltan datos requeridos, incluyendo el Ingeniero a Cargo"}), 400
        
    if tipo_registro not in ['Entrada', 'Salida']:
        return jsonify({"error": "Tipo de registro inválido"}), 400

    if tipo_registro == 'Salida' and not actividades_diarias.strip():
        return jsonify({"error": "Las actividades diarias son obligatorias al registrar la salida"}), 400
        
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO registros_tiempo 
                (nombre_tecnico, ingeniero_a_cargo, tipo_registro, latitud, longitud, precision_gps, actividades_diarias)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (nombre_tecnico, ingeniero_a_cargo, tipo_registro, latitud, longitud, precision_gps, actividades_diarias))
        connection.commit()
        logging.info(f"Registro exitoso: {nombre_tecnico} marcó {tipo_registro} con Ing. {ingeniero_a_cargo}")
    except Exception as e:
        logging.error(f"Error de BD al registrar asistencia para {nombre_tecnico}: {str(e)}")
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
                logging.info(f"Admin inició sesión: {usuario}")
                return redirect(url_for('dashboard'))
            else:
                flash('Credenciales incorrectas.', 'error')
        except Exception as e:
            logging.error(f"Error de base de datos en login de admin: {str(e)}")
            flash('Error de conexión.', 'error')
        finally:
            if 'connection' in locals() and connection.open:
                connection.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    usuario = session.get('admin_user', 'Desconocido')
    session.pop('admin_logged_in', None)
    session.pop('admin_user', None)
    logging.info(f"Admin cerró sesión: {usuario}")
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@admin_login_required
def dashboard():
    registros = []
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM registros_tiempo ORDER BY marca_de_tiempo DESC"
            cursor.execute(sql)
            registros = cursor.fetchall()
    except Exception as e:
        logging.error(f"Error al cargar dashboard: {str(e)}")
        flash('Error al cargar registros.', 'error')
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()
    return render_template('dashboard.html', registros=registros)

@app.route('/admin/exportar')
@admin_login_required
def exportar():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM registros_tiempo ORDER BY marca_de_tiempo DESC"
            cursor.execute(sql)
            registros = cursor.fetchall()
            
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Registros Completos"
        
        headers = ["ID", "Nombre Técnico", "Ingeniero a Cargo", "Tipo Registro", "Latitud", "Longitud", "Precisión GPS", "Actividades Diarias", "Marca de Tiempo"]
        ws.append(headers)
        
        for r in registros:
            fecha = r['marca_de_tiempo'].replace(tzinfo=None) if hasattr(r['marca_de_tiempo'], 'tzinfo') else r['marca_de_tiempo']
            ws.append([
                r['id'], 
                r['nombre_tecnico'], 
                r.get('ingeniero_a_cargo', ''),
                r['tipo_registro'], 
                float(r['latitud']), 
                float(r['longitud']), 
                float(r['precision_gps']), 
                r.get('actividades_diarias', ''),
                fecha
            ])
            
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        logging.info(f"Admin {session.get('admin_user')} exportó los registros a Excel.")
        
        return send_file(
            output,
            as_attachment=True,
            download_name="registros_asistencia_completo.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logging.error(f"Error al exportar Excel: {str(e)}")
        return f"Error al exportar: {str(e)}", 500
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
