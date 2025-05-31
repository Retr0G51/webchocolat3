from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
from urllib.parse import quote_plus
import requests
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuración de base de datos
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Para Railway con PostgreSQL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    logger.info(f"✅ Usando PostgreSQL")
else:
    # Para desarrollo local con SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chocolates_byb.db'
    logger.info("✅ Usando SQLite local")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)

# Modelos de la base de datos
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    tamaño = db.Column(db.String(20))
    peso = db.Column(db.Integer)
    precio_venta = db.Column(db.Integer, nullable=False)
    costo_produccion = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)

class Trabajador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    telefono = db.Column(db.String(20))
    total_ganado = db.Column(db.Integer, default=0)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_orden = db.Column(db.Integer, unique=True, nullable=False)
    fecha_pedido = db.Column(db.Date, nullable=False, default=date.today)
    fecha_entrega = db.Column(db.Date, nullable=False)
    horario_entrega = db.Column(db.String(20))
    cliente_nombre = db.Column(db.String(100), nullable=False)
    cliente_telefono = db.Column(db.String(20))
    cliente_direccion = db.Column(db.Text)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('trabajador.id'))
    mensajero_id = db.Column(db.Integer, db.ForeignKey('trabajador.id'))
    elaborador_id = db.Column(db.Integer, db.ForeignKey('trabajador.id'))
    estado = db.Column(db.String(20), default='PENDIENTE')
    modificado = db.Column(db.Boolean, default=False)
    subtotal = db.Column(db.Integer, nullable=False)
    mensajeria = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)
    observaciones = db.Column(db.Text)
    
    vendedor = db.relationship('Trabajador', foreign_keys=[vendedor_id])
    mensajero = db.relationship('Trabajador', foreign_keys=[mensajero_id])
    elaborador = db.relationship('Trabajador', foreign_keys=[elaborador_id])

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Integer, nullable=False)
    incluye_bolsa_regalo = db.Column(db.Boolean, default=False)
    precio_bolsa = db.Column(db.Integer, default=0)
    
    pedido = db.relationship('Pedido', backref='items')
    producto = db.relationship('Producto')

class ComisionPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    trabajador_id = db.Column(db.Integer, db.ForeignKey('trabajador.id'))
    tipo_comision = db.Column(db.String(30), nullable=False)
    monto = db.Column(db.Integer, nullable=False)
    
    pedido = db.relationship('Pedido')
    trabajador = db.relationship('Trabajador')

class ConfiguracionComisiones(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comision_vendedor = db.Column(db.Integer, default=500)
    ganancia_negocio = db.Column(db.Integer, default=200)
    ganancia_inversores = db.Column(db.Integer, default=500)
    precio_bolsa_regalo = db.Column(db.Integer, default=200)

# Funciones auxiliares
def calcular_comisiones_pedido(pedido):
    """Calcula las comisiones de un pedido completado"""
    config = ConfiguracionComisiones.query.first()
    if not config:
        config = ConfiguracionComisiones()
        db.session.add(config)
        db.session.commit()
    
    # Limpiar comisiones existentes
    ComisionPedido.query.filter_by(pedido_id=pedido.id).delete()
    
    # Calcular inversión total (costos de producción)
    inversion_total = 0
    for item in pedido.items:
        inversion_total += item.producto.costo_produccion * item.cantidad
    
    comisiones = []
    
    # Vendedor
    if pedido.vendedor_id:
        comision = ComisionPedido(
            pedido_id=pedido.id,
            trabajador_id=pedido.vendedor_id,
            tipo_comision='VENDEDOR',
            monto=config.comision_vendedor
        )
        comisiones.append(comision)
    
    # Mensajero
    if pedido.mensajero_id and pedido.mensajeria > 0:
        comision = ComisionPedido(
            pedido_id=pedido.id,
            trabajador_id=pedido.mensajero_id,
            tipo_comision='MENSAJERO',
            monto=pedido.mensajeria
        )
        comisiones.append(comision)
    
    # Elaborador
    if pedido.elaborador_id:
        comision_elaborador = 0
        for item in pedido.items:
            # Comisión por producto elaborado (ejemplo: 100 CUP por producto)
            comision_elaborador += 100 * item.cantidad
        
        comision = ComisionPedido(
            pedido_id=pedido.id,
            trabajador_id=pedido.elaborador_id,
            tipo_comision='ELABORADOR',
            monto=comision_elaborador
        )
        comisiones.append(comision)
    
    # Ganancias del negocio
    comision = ComisionPedido(
        pedido_id=pedido.id,
        trabajador_id=None,
        tipo_comision='GANANCIA_NEGOCIO',
        monto=config.ganancia_negocio
    )
    comisiones.append(comision)
    
    # Ganancias de inversores (dividido equitativamente)
    inversores = Trabajador.query.filter_by(tipo='inversor', activo=True).all()
    if inversores:
        ganancia_por_inversor = config.ganancia_inversores // len(inversores)
        for inversor in inversores:
            comision = ComisionPedido(
                pedido_id=pedido.id,
                trabajador_id=inversor.id,
                tipo_comision='GANANCIA_INVERSOR',
                monto=ganancia_por_inversor
            )
            comisiones.append(comision)
    
    # Inversión
    comision = ComisionPedido(
        pedido_id=pedido.id,
        trabajador_id=None,
        tipo_comision='INVERSION',
        monto=inversion_total
    )
    comisiones.append(comision)
    
    # Guardar todas las comisiones
    for comision in comisiones:
        db.session.add(comision)
    
    db.session.commit()
    return comisiones

def enviar_whatsapp(numero, mensaje):
    """Envía mensaje por WhatsApp usando CallMeBot API"""
    api_key = os.environ.get('CALLMEBOT_API_KEY')
    if not api_key:
        print("API Key de CallMeBot no configurada")
        return False
    
    try:
        url = f"https://api.callmebot.com/whatsapp.php"
        params = {
            'phone': numero,
            'text': mensaje,
            'apikey': api_key
        }
        response = requests.get(url, params=params)
        return response.status_code == 200
    except Exception as e:
        print(f"Error enviando WhatsApp: {e}")
        return False

def generar_reporte_pedido(pedido):
    """Genera el reporte individual de un pedido"""
    comisiones = ComisionPedido.query.filter_by(pedido_id=pedido.id).all()
    
    mensaje = f"""🔸 *[{pedido.numero_orden}] Reporte Financiero* 🏷️
💰 Total facturado: {pedido.total} CUP

📊 DISTRIBUCIÓN:
"""
    
    for comision in comisiones:
        if comision.tipo_comision == 'VENDEDOR' and comision.trabajador:
            mensaje += f"👤 VENDEDOR ({comision.trabajador.nombre}): {comision.monto} CUP\n"
        elif comision.tipo_comision == 'MENSAJERO' and comision.trabajador:
            mensaje += f"🛵 MENSAJERO ({comision.trabajador.nombre}): {comision.monto} CUP\n"
        elif comision.tipo_comision == 'ELABORADOR' and comision.trabajador:
            mensaje += f"👨‍🍳 ELABORADOR ({comision.trabajador.nombre}): {comision.monto} CUP\n"
        elif comision.tipo_comision == 'GANANCIA_NEGOCIO':
            mensaje += f"🏢 GANANCIAS NEGOCIO: {comision.monto} CUP\n"
        elif comision.tipo_comision == 'GANANCIA_INVERSOR' and comision.trabajador:
            mensaje += f"💼 GANANCIA INVERSOR ({comision.trabajador.nombre}): {comision.monto} CUP\n"
        elif comision.tipo_comision == 'INVERSION':
            mensaje += f"🏭 INVERSIÓN: {comision.monto} CUP\n"
    
    return mensaje

def generar_reporte_diario():
    """Genera el reporte diario consolidado"""
    pedidos_hoy = Pedido.query.filter(
        Pedido.fecha_pedido == date.today(),
        Pedido.estado == 'COMPLETADO'
    ).all()
    
    if not pedidos_hoy:
        return "📊 No hay pedidos completados hoy"
    
    total_facturado = sum(p.total for p in pedidos_hoy)
    
    mensaje = f"""📊 *REPORTE DIARIO - {date.today().strftime('%d/%m/%Y')}*

🔢 Pedidos completados: {len(pedidos_hoy)}
💰 Total facturado: {total_facturado} CUP

📋 PEDIDOS:
"""
    
    for pedido in pedidos_hoy:
        mensaje += f"• [{pedido.numero_orden}] {pedido.cliente_nombre}: {pedido.total} CUP\n"
    
    # Consolidado de ganancias por trabajador
    ganancias_trabajadores = {}
    for pedido in pedidos_hoy:
        comisiones = ComisionPedido.query.filter_by(pedido_id=pedido.id).all()
        for comision in comisiones:
            if comision.trabajador_id and comision.trabajador:
                nombre = comision.trabajador.nombre
                if nombre not in ganancias_trabajadores:
                    ganancias_trabajadores[nombre] = 0
                ganancias_trabajadores[nombre] += comision.monto
    
    if ganancias_trabajadores:
        mensaje += "\n👥 GANANCIAS POR TRABAJADOR:\n"
        for nombre, ganancia in ganancias_trabajadores.items():
            mensaje += f"• {nombre}: {ganancia} CUP\n"
    
    return mensaje

# Rutas
@app.route('/')
def index():
    try:
        # Obtener estadísticas para el dashboard
        pedidos_hoy = Pedido.query.filter(
            Pedido.fecha_pedido == date.today(),
            Pedido.estado == 'COMPLETADO'
        ).count()
        
        total_hoy = sum(p.total for p in Pedido.query.filter(
            Pedido.fecha_pedido == date.today(),
            Pedido.estado == 'COMPLETADO'
        ).all()) or 0
        
        pedidos_pendientes = Pedido.query.filter_by(estado='PENDIENTE').count()
        trabajadores_activos = Trabajador.query.filter_by(activo=True).count()
        
        return render_template('index.html',
                             pedidos_hoy=pedidos_hoy,
                             total_hoy=total_hoy,
                             pedidos_pendientes=pedidos_pendientes,
                             trabajadores_activos=trabajadores_activos)
    except Exception as e:
        # En caso de error, mostrar dashboard básico
        logger.error(f"Error en dashboard: {e}")
        return render_template('index.html',
                             pedidos_hoy=0,
                             total_hoy=0,
                             pedidos_pendientes=0,
                             trabajadores_activos=0)

@app.route('/api/estadisticas')
def api_estadisticas():
    pedidos_hoy = Pedido.query.filter(
        Pedido.fecha_pedido == date.today(),
        Pedido.estado == 'COMPLETADO'
    ).count()
    
    total_hoy = sum(p.total for p in Pedido.query.filter(
        Pedido.fecha_pedido == date.today(),
        Pedido.estado == 'COMPLETADO'
    ).all()) or 0
    
    pedidos_pendientes = Pedido.query.filter_by(estado='PENDIENTE').count()
    trabajadores_activos = Trabajador.query.filter_by(activo=True).count()
    
    return jsonify({
        'pedidos_hoy': pedidos_hoy,
        'total_hoy': total_hoy,
        'pedidos_pendientes': pedidos_pendientes,
        'trabajadores_activos': trabajadores_activos
    })

@app.route('/pedidos')
def pedidos():
    pedidos = Pedido.query.order_by(Pedido.numero_orden.desc()).all()
    trabajadores = Trabajador.query.filter_by(activo=True).all()
    productos = Producto.query.filter_by(activo=True).all()
    return render_template('pedidos.html', pedidos=pedidos, trabajadores=trabajadores, productos=productos)

@app.route('/crear_pedido', methods=['POST'])
def crear_pedido():
    try:
        # Obtener el siguiente número de orden
        ultimo_pedido = Pedido.query.order_by(Pedido.numero_orden.desc()).first()
        numero_orden = (ultimo_pedido.numero_orden + 1) if ultimo_pedido else 1
        
        # Crear el pedido
        pedido = Pedido(
            numero_orden=numero_orden,
            fecha_entrega=datetime.strptime(request.form['fecha_entrega'], '%Y-%m-%d').date(),
            horario_entrega=request.form.get('horario_entrega'),
            cliente_nombre=request.form['cliente_nombre'],
            cliente_telefono=request.form.get('cliente_telefono'),
            cliente_direccion=request.form['cliente_direccion'],
            vendedor_id=request.form.get('vendedor_id') or None,
            mensajero_id=request.form.get('mensajero_id') or None,
            elaborador_id=request.form.get('elaborador_id') or None,
            mensajeria=int(request.form.get('mensajeria', 0)),
            observaciones=request.form.get('observaciones'),
            subtotal=0,
            total=0
        )
        
        db.session.add(pedido)
        db.session.flush()  # Para obtener el ID
        
        # Procesar productos
        productos_ids = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        precios = request.form.getlist('precios[]')
        
        subtotal = 0
        for i, producto_id in enumerate(productos_ids):
            if producto_id:
                cantidad = int(cantidades[i]) if cantidades[i] else 1
                precio_unitario = int(precios[i]) if precios[i] else 0
                
                item = ItemPedido(
                    pedido_id=pedido.id,
                    producto_id=int(producto_id),
                    cantidad=cantidad,
                    precio_unitario=precio_unitario // cantidad if cantidad > 0 else 0
                )
                db.session.add(item)
                subtotal += precio_unitario
        
        pedido.subtotal = subtotal
        pedido.total = subtotal + pedido.mensajeria
        
        db.session.commit()
        flash('Pedido creado exitosamente', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear pedido: {str(e)}', 'error')
    
    return redirect(url_for('pedidos'))

@app.route('/completar_pedido/<int:pedido_id>')
def completar_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.estado != 'COMPLETADO':
        pedido.estado = 'COMPLETADO'
        db.session.commit()
        
        # Calcular comisiones
        calcular_comisiones_pedido(pedido)
        
        # Enviar reporte por WhatsApp
        admin_phone = os.environ.get('ADMIN_PHONE')
        if admin_phone:
            mensaje = generar_reporte_pedido(pedido)
            enviar_whatsapp(admin_phone, mensaje)
        
        flash('Pedido completado y reporte enviado por WhatsApp', 'success')
    
    return redirect(url_for('pedidos'))

@app.route('/reporte_diario')
def reporte_diario():
    mensaje = generar_reporte_diario()
    
    # Enviar por WhatsApp
    admin_phone = os.environ.get('ADMIN_PHONE')
    if admin_phone:
        enviar_whatsapp(admin_phone, mensaje)
        flash('Reporte diario enviado por WhatsApp', 'success')
    else:
        flash('Número de administrador no configurado', 'warning')
    
    return redirect(url_for('index'))

@app.route('/trabajadores')
def trabajadores():
    trabajadores = Trabajador.query.filter_by(activo=True).all()
    return render_template('trabajadores.html', trabajadores=trabajadores)

@app.route('/crear_trabajador', methods=['POST'])
def crear_trabajador():
    try:
        trabajador = Trabajador(
            nombre=request.form['nombre'],
            tipo=request.form['tipo'],
            telefono=request.form.get('telefono')
        )
        db.session.add(trabajador)
        db.session.commit()
        flash('Trabajador creado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear trabajador: {str(e)}', 'error')
    
    return redirect(url_for('trabajadores'))

@app.route('/productos')
def productos():
    productos = Producto.query.filter_by(activo=True).all()
    return render_template('productos.html', productos=productos)

@app.route('/crear_producto', methods=['POST'])
def crear_producto():
    try:
        producto = Producto(
            nombre=request.form['nombre'],
            tipo=request.form['tipo'],
            tamaño=request.form.get('tamaño'),
            precio_venta=int(request.form['precio_venta']),
            costo_produccion=int(request.form['costo_produccion']),
            stock=int(request.form.get('stock', 0))
        )
        db.session.add(producto)
        db.session.commit()
        flash('Producto creado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al crear producto: {str(e)}', 'error')
    
    return redirect(url_for('productos'))

@app.route('/configuracion')
def configuracion():
    config = ConfiguracionComisiones.query.first()
    if not config:
        config = ConfiguracionComisiones()
        db.session.add(config)
        db.session.commit()
    return render_template('configuracion.html', config=config)

@app.route('/actualizar_configuracion', methods=['POST'])
def actualizar_configuracion():
    try:
        config = ConfiguracionComisiones.query.first()
        if not config:
            config = ConfiguracionComisiones()
        
        config.comision_vendedor = int(request.form['comision_vendedor'])
        config.ganancia_negocio = int(request.form['ganancia_negocio'])
        config.ganancia_inversores = int(request.form['ganancia_inversores'])
        config.precio_bolsa_regalo = int(request.form['precio_bolsa_regalo'])
        
        db.session.add(config)
        db.session.commit()
        flash('Configuración actualizada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar configuración: {str(e)}', 'error')
    
    return redirect(url_for('configuracion'))

# Ruta de healthcheck para Railway
@app.route('/health')
def health_check():
    try:
        # Verificar conexión a base de datos
        db.session.execute('SELECT 1')
        return {'status': 'ok', 'app': 'Chocolates ByB', 'database': 'connected'}, 200
    except Exception as e:
        logger.error(f"Healthcheck failed: {e}")
        return {'status': 'error', 'message': str(e)}, 500

# Test simple sin base de datos
@app.route('/ping')
def ping():
    return {'status': 'pong', 'timestamp': datetime.now().isoformat()}, 200

# Inicializar base de datos
def init_db():
    """Inicializa la base de datos con datos de ejemplo"""
    try:
        logger.info("Initializing database...")
        
        # Crear todas las tablas
        db.create_all()
        logger.info("Tables created successfully")
        
        # Verificar si ya hay datos
        if Trabajador.query.first():
            logger.info("Database already has data")
            return
        
        logger.info("Creating sample data...")
        
        # Trabajadores de ejemplo
        trabajadores = [
            Trabajador(nombre='Vendedor Principal', tipo='vendedor'),
            Trabajador(nombre='Mensajero 1', tipo='mensajero'),
            Trabajador(nombre='Elaborador Principal', tipo='elaborador'),
            Trabajador(nombre='Inversor 1', tipo='inversor'),
            Trabajador(nombre='Inversor 2', tipo='inversor')
        ]
        
        for trabajador in trabajadores:
            db.session.add(trabajador)
        
        # Productos de ejemplo
        productos = [
            Producto(
                nombre='Chocolate Grande',
                tipo='chocolate',
                tamaño='grande',
                precio_venta=1900,
                costo_produccion=800
            ),
            Producto(
                nombre='Chocolate Mediano',
                tipo='chocolate',
                tamaño='mediano',
                precio_venta=1200,
                costo_produccion=500
            )
        ]
        
        for producto in productos:
            db.session.add(producto)
        
        # Configuración inicial
        config = ConfiguracionComisiones()
        db.session.add(config)
        
        db.session.commit()
        logger.info("Sample data created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.session.rollback()

# Función para crear tablas al iniciar
@app.before_first_request
def create_tables():
    """Crea las tablas antes de la primera petición"""
    try:
        with app.app_context():
            init_db()
    except Exception as e:
        logger.error(f"Error in create_tables: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting server on port {port}")
    logger.info(f"Debug mode: {debug_mode}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
