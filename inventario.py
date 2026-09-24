from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pymysql
from functools import wraps

app = Flask(__name__)
app.secret_key = "sannet_solutions_t3c"

# contenido del archivo .env
# en este caso se trabajo en mysql, pero se puede cambiar a postgresql o cualquier otro motor de base de datos compatible con SQLAlchemy

def get_db_connection():
    return pymysql.connect(
        host='direcion_ip_del_servidor',
        port= puerto_de_la_base_de_datos,
        user='usuario_de_la_base_de_datos',
        password='contraseña_de_la_base_de_datos',
        db='nombre_de_la_base_de_datos',
        cursorclass= pymysql.cursors.DictCursor
    )

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('usuario')
        pw = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s AND password = %s", (user, pw))
        usuario_db = cursor.fetchone()
        conn.close()

        if usuario_db:
            session['user_id'] = usuario_db['id']
            session['user_name'] = usuario_db['usuario']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Credenciales inválidas")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT p.*, c.nombre AS categoria_nombre, d.nombre AS deposito_nombre
            FROM productos p 
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN depositos d ON p.deposito_id = d.id
            ORDER BY p.id DESC
        """
        cursor.execute(query)
        productos = cursor.fetchall()
        cursor.execute("SELECT * FROM categorias ORDER BY nombre ASC")
        categorias = cursor.fetchall()
        cursor.execute("SELECT * FROM depositos ORDER BY nombre ASC")
        depositos = cursor.fetchall()
        return render_template('inventario.html', productos=productos, categorias=categorias, depositos=depositos)
    finally:
        conn.close()

@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    conn = get_db_connection()
    cursor = conn.cursor()
    d = request.form
    try:
        sql = """INSERT INTO productos (nombre, marca, serial, precio_usd, precio_bs, stock, categoria_id, deposito_id, especificaciones) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (d['nombre'], d['marca'], d['serial'], d['precio_usd'], d['precio_bs'], d['stock'], d.get('categoria_id'), d.get('deposito_id'), d.get('especificaciones')))
        nuevo_id = conn.insert_id()
        conn.commit()
        
        cursor.execute("""
            SELECT p.*, c.nombre AS cat_n, d.nombre AS dep_n 
            FROM productos p 
            LEFT JOIN categorias c ON p.categoria_id = c.id 
            LEFT JOIN depositos d ON p.deposito_id = d.id 
            WHERE p.id = %s""", (nuevo_id,))
        return jsonify({"success": True, "producto": cursor.fetchone()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()

@app.route('/editar/<int:id>', methods=['POST'])
@login_required
def editar(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    d = request.form
    try:
        sql = """UPDATE productos SET nombre=%s, marca=%s, serial=%s, precio_usd=%s, precio_bs=%s, stock=%s, categoria_id=%s, deposito_id=%s, especificaciones=%s WHERE id=%s"""
        cursor.execute(sql, (d['nombre'], d['marca'], d['serial'], d['precio_usd'], d['precio_bs'], d['stock'], d.get('categoria_id'), d.get('deposito_id'), d.get('especificaciones'), id))
        conn.commit()
        
        cursor.execute("""
            SELECT p.*, c.nombre AS cat_n, d.nombre AS dep_n 
            FROM productos p 
            LEFT JOIN categorias c ON p.categoria_id = c.id 
            LEFT JOIN depositos d ON p.deposito_id = d.id 
            WHERE p.id = %s""", (id,))
        return jsonify({"success": True, "producto": cursor.fetchone()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    finally:
        conn.close()

@app.route('/modificar_stock_ajax/<int:id>/<string:operacion>', methods=['POST'])
@login_required
def modificar_stock_ajax(id, operacion):
    cantidad = int(request.form.get('cantidad', 1))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if operacion == 'sumar':
            cursor.execute("UPDATE productos SET stock = stock + %s WHERE id = %s", (cantidad, id))
        else:
            cursor.execute("UPDATE productos SET stock = GREATEST(0, stock - %s) WHERE id = %s", (cantidad, id))
        conn.commit()
        cursor.execute("SELECT stock FROM productos WHERE id = %s", (id,))
        return jsonify({"success": True, "nuevo_stock": cursor.fetchone()['stock']})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)