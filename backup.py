#!/usr/bin/env python3
"""
Script de backup para Chocolates ByB
Genera un backup de la base de datos en formato JSON
"""

import json
import os
from datetime import datetime
from app import app, db, Pedido, Trabajador, Producto, ItemPedido, ComisionPedido, ConfiguracionComisiones

def backup_database():
    """Genera un backup completo de la base de datos"""
    
    with app.app_context():
        backup_data = {
            'fecha_backup': datetime.now().isoformat(),
            'version': '1.0',
            'datos': {}
        }
        
        # Backup de trabajadores
        trabajadores = []
        for trabajador in Trabajador.query.all():
            trabajadores.append({
                'id': trabajador.id,
                'nombre': trabajador.nombre,
                'tipo': trabajador.tipo,
                'activo': trabajador.activo,
                'telefono': trabajador.telefono,
                'total_ganado': trabajador.total_ganado
            })
        backup_data['datos']['trabajadores'] = trabajadores
        
        # Backup de productos
        productos = []
        for producto in Producto.query.all():
            productos.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'tipo': producto.tipo,
                'tamaño': producto.tamaño,
                'peso': producto.peso,
                'precio_venta': producto.precio_venta,
                'costo_produccion': producto.costo_produccion,
                'stock': producto.stock,
                'activo': producto.activo
            })
        backup_data['datos']['productos'] = productos
        
        # Backup de pedidos
        pedidos = []
        for pedido in Pedido.query.all():
            pedido_data = {
                'id': pedido.id,
                'numero_orden': pedido.numero_orden,
                'fecha_pedido': pedido.fecha_pedido.isoformat() if pedido.fecha_pedido else None,
                'fecha_entrega': pedido.fecha_entrega.isoformat() if pedido.fecha_entrega else None,
                'horario_entrega': pedido.horario_entrega,
                'cliente_nombre': pedido.cliente_nombre,
                'cliente_telefono': pedido.cliente_telefono,
                'cliente_direccion': pedido.cliente_direccion,
                'vendedor_id': pedido.vendedor_id,
                'mensajero_id': pedido.mensajero_id,
                'elaborador_id': pedido.elaborador_id,
                'estado': pedido.estado,
                'modificado': pedido.modificado,
                'subtotal': pedido.subtotal,
                'mensajeria': pedido.mensajeria,
                'total': pedido.total,
                'observaciones': pedido.observaciones,
                'items': []
            }
            
            # Items del pedido
            for item in pedido.items:
                pedido_data['items'].append({
                    'producto_id': item.producto_id,
                    'cantidad': item.cantidad,
                    'precio_unitario': item.precio_unitario,
                    'incluye_bolsa_regalo': item.incluye_bolsa_regalo,
                    'precio_bolsa': item.precio_bolsa
                })
            
            pedidos.append(pedido_data)
        backup_data['datos']['pedidos'] = pedidos
        
        # Backup de comisiones
        comisiones = []
        for comision in ComisionPedido.query.all():
            comisiones.append({
                'pedido_id': comision.pedido_id,
                'trabajador_id': comision.trabajador_id,
                'tipo_comision': comision.tipo_comision,
                'monto': comision.monto
            })
        backup_data['datos']['comisiones'] = comisiones
        
        # Backup de configuración
        config = ConfiguracionComisiones.query.first()
        if config:
            backup_data['datos']['configuracion'] = {
                'comision_vendedor': config.comision_vendedor,
                'ganancia_negocio': config.ganancia_negocio,
                'ganancia_inversores': config.ganancia_inversores,
                'precio_bolsa_regalo': config.precio_bolsa_regalo
            }
        
        # Guardar backup
        fecha_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_chocolates_byb_{fecha_str}.json'
        
        # Crear directorio de backup si no existe
        os.makedirs('backup', exist_ok=True)
        filepath = os.path.join('backup', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Backup creado exitosamente: {filepath}")
        print(f"📊 Estadísticas del backup:")
        print(f"   - Trabajadores: {len(trabajadores)}")
        print(f"   - Productos: {len(productos)}")
        print(f"   - Pedidos: {len(pedidos)}")
        print(f"   - Comisiones: {len(comisiones)}")
        
        return filepath

def restore_database(backup_file):
    """Restaura la base de datos desde un archivo de backup"""
    
    if not os.path.exists(backup_file):
        print(f"❌ Archivo de backup no encontrado: {backup_file}")
        return False
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        with app.app_context():
            print("⚠️  ADVERTENCIA: Esta operación eliminará todos los datos actuales")
            confirm = input("¿Está seguro que desea continuar? (SI/no): ")
            
            if confirm.upper() != 'SI':
                print("❌ Operación cancelada")
                return False
            
            # Limpiar tablas
            ComisionPedido.query.delete()
            ItemPedido.query.delete()
            Pedido.query.delete()
            Producto.query.delete()
            Trabajador.query.delete()
            ConfiguracionComisiones.query.delete()
            
            datos = backup_data['datos']
            
            # Restaurar trabajadores
            for t_data in datos.get('trabajadores', []):
                trabajador = Trabajador(
                    nombre=t_data['nombre'],
                    tipo=t_data['tipo'],
                    activo=t_data['activo'],
                    telefono=t_data['telefono'],
                    total_ganado=t_data['total_ganado']
                )
                db.session.add(trabajador)
            
            # Restaurar productos
            for p_data in datos.get('productos', []):
                producto = Producto(
                    nombre=p_data['nombre'],
                    tipo=p_data['tipo'],
                    tamaño=p_data['tamaño'],
                    peso=p_data['peso'],
                    precio_venta=p_data['precio_venta'],
                    costo_produccion=p_data['costo_produccion'],
                    stock=p_data['stock'],
                    activo=p_data['activo']
                )
                db.session.add(producto)
            
            db.session.commit()
            
            # Restaurar pedidos
            for ped_data in datos.get('pedidos', []):
                pedido = Pedido(
                    numero_orden=ped_data['numero_orden'],
                    fecha_pedido=datetime.fromisoformat(ped_data['fecha_pedido']).date() if ped_data['fecha_pedido'] else None,
                    fecha_entrega=datetime.fromisoformat(ped_data['fecha_entrega']).date() if ped_data['fecha_entrega'] else None,
                    horario_entrega=ped_data['horario_entrega'],
                    cliente_nombre=ped_data['cliente_nombre'],
                    cliente_telefono=ped_data['cliente_telefono'],
                    cliente_direccion=ped_data['cliente_direccion'],
                    vendedor_id=ped_data['vendedor_id'],
                    mensajero_id=ped_data['mensajero_id'],
                    elaborador_id=ped_data['elaborador_id'],
                    estado=ped_data['estado'],
                    modificado=ped_data['modificado'],
                    subtotal=ped_data['subtotal'],
                    mensajeria=ped_data['mensajeria'],
                    total=ped_data['total'],
                    observaciones=ped_data['observaciones']
                )
                db.session.add(pedido)
                db.session.flush()
                
                # Restaurar items del pedido
                for item_data in ped_data.get('items', []):
                    item = ItemPedido(
                        pedido_id=pedido.id,
                        producto_id=item_data['producto_id'],
                        cantidad=item_data['cantidad'],
                        precio_unitario=item_data['precio_unitario'],
                        incluye_bolsa_regalo=item_data['incluye_bolsa_regalo'],
                        precio_bolsa=item_data['precio_bolsa']
                    )
                    db.session.add(item)
            
            # Restaurar comisiones
            for com_data in datos.get('comisiones', []):
                comision = ComisionPedido(
                    pedido_id=com_data['pedido_id'],
                    trabajador_id=com_data['trabajador_id'],
                    tipo_comision=com_data['tipo_comision'],
                    monto=com_data['monto']
                )
                db.session.add(comision)
            
            # Restaurar configuración
            config_data = datos.get('configuracion')
            if config_data:
                config = ConfiguracionComisiones(
                    comision_vendedor=config_data['comision_vendedor'],
                    ganancia_negocio=config_data['ganancia_negocio'],
                    ganancia_inversores=config_data['ganancia_inversores'],
                    precio_bolsa_regalo=config_data['precio_bolsa_regalo']
                )
                db.session.add(config)
            
            db.session.commit()
            
            print(f"✅ Base de datos restaurada exitosamente desde: {backup_file}")
            print(f"📅 Fecha del backup: {backup_data['fecha_backup']}")
            return True
            
    except Exception as e:
        print(f"❌ Error restaurando backup: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python backup.py backup                    # Crear backup")
        print("  python backup.py restore <archivo>         # Restaurar backup")
        sys.exit(1)
    
    comando = sys.argv[1].lower()
    
    if comando == "backup":
        backup_database()
    elif comando == "restore":
        if len(sys.argv) < 3:
            print("❌ Especifique el archivo de backup")
            sys.exit(1)
        restore_database(sys.argv[2])
    else:
        print("❌ Comando no válido. Use 'backup' o 'restore'")
        sys.exit(1)
