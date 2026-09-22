from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ot_sistema_2026_clave_secreta'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

DB = 'ot_sistema.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def generar_codigo_ot():
    fecha = datetime.now().strftime('%Y%m%d')
    return f'OT-COM-{fecha}'

# ==================== AUTENTICACIÓN ====================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM usuarios WHERE username=? AND activo=1', 
            (username,)
        ).fetchone()
        conn.close()
        
        if user and user['password'] == password:
            session['usuario_id'] = user['id']
            session['usuario_nombre'] = user['nombre']
            session['usuario_rol'] = user['rol']
            
            if user['rol'] == 'COORDINADOR':
                return redirect(url_for('dashboard_coordinador'))
            else:
                return redirect(url_for('dashboard_ejecutor'))
        else:
            flash('❌ Credenciales inválidas', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== DASHBOARD COORDINADOR ====================
@app.route('/dashboard_coordinador')
def dashboard_coordinador():
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    conn = get_db()
    ots = conn.execute('SELECT * FROM vw_ot_resumen').fetchall()
    conn.close()
    
    return render_template('dashboard_coordinador.html', ots=ots)

# ==================== DASHBOARD EJECUTOR ====================
@app.route('/dashboard_ejecutor')
def dashboard_ejecutor():
    if 'usuario_id' not in session or session['usuario_rol'] != 'EJECUTOR':
        return redirect(url_for('login'))
    
    ejecutor_id = session['usuario_id']
    conn = get_db()
    ots = conn.execute(
        'SELECT * FROM vw_ot_resumen WHERE ejecutor_id=?', 
        (ejecutor_id,)
    ).fetchall()
    conn.close()
    
    return render_template('dashboard_ejecutor.html', ots=ots)

# ==================== CREAR OT ====================
@app.route('/crear_ot', methods=['GET', 'POST'])
def crear_ot():
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        codigo = generar_codigo_ot()
        
        conn = get_db()
        conn.execute('''
            INSERT INTO ordenes_trabajo 
            (codigo_ot, tipo_ot, prioridad, activo_canal_afectado, subestacion_nodo,
             medio, sistema_scada_afectado, fecha_creacion, hora_creacion,
             descripcion_falla, ejecutor_id, estado, solicitado_por, aprobado_por)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ASIGNADA', ?, ?)
        ''', (
            codigo, request.form.get('tipo_ot'), request.form.get('prioridad'),
            request.form.get('activo_canal_afectado'), request.form.get('subestacion_nodo'),
            request.form.get('medio'), request.form.get('sistema_scada_afectado'),
            request.form.get('fecha_creacion'), request.form.get('hora_creacion'),
            request.form.get('descripcion_falla'), request.form.get('ejecutor_id'),
            request.form.get('solicitado_por'), request.form.get('aprobado_por')
        ))
        
        ot_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Crear registros de documentos con estado inicial
        for tipo in ['OT', 'INFORME_FALLA', 'CERTIFICACION', 'ACTA_ENTREGA']:
            conn.execute('''
                INSERT INTO ot_documentos_estado (ot_id, tipo_documento, incluir, estado)
                VALUES (?, ?, 1, 'PENDIENTE')
            ''', (ot_id, tipo))
        
        conn.commit()
        conn.close()
        
        flash(f'✅ OT {codigo} creada exitosamente', 'success')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    conn = get_db()
    ejecutores = conn.execute(
        "SELECT id, nombre FROM usuarios WHERE rol='EJECUTOR' AND activo=1"
    ).fetchall()
    conn.close()
    
    return render_template('crear_ot.html', ejecutores=ejecutores)

# ==================== VER OT (SELECTOR DE DOCUMENTOS) ====================
@app.route('/ot/<int:ot_id>')
def ver_ot(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    ot = conn.execute('SELECT * FROM ordenes_trabajo WHERE id=?', (ot_id,)).fetchone()
    
    if not ot:
        flash('❌ OT no encontrada', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    # Validar acceso
    if session['usuario_rol'] == 'EJECUTOR' and ot['ejecutor_id'] != session['usuario_id']:
        flash('❌ No tienes acceso a esta OT', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    documentos = conn.execute(
        'SELECT * FROM vw_estado_documentos WHERE ot_id=?', 
        (ot_id,)
    ).fetchone()
    conn.close()
    
    return render_template('ver_ot.html', ot=ot, documentos=documentos)

# ==================== ACTUALIZAR ESTADO DE DOCUMENTOS ====================
@app.route('/actualizar_documentos/<int:ot_id>', methods=['POST'])
def actualizar_documentos(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    tipos = ['OT', 'INFORME_FALLA', 'CERTIFICACION', 'ACTA_ENTREGA']
    
    conn = get_db()
    for tipo in tipos:
        incluir = 1 if request.form.get(f'incluir_{tipo}') else 0
        estado = 'NO_APLICA' if incluir == 0 else 'PENDIENTE'
        
        conn.execute('''
            INSERT INTO ot_documentos_estado (ot_id, tipo_documento, incluir, estado)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ot_id, tipo_documento) 
            DO UPDATE SET incluir=excluded.incluir, estado=excluded.estado, 
                          fecha_actualizacion=CURRENT_TIMESTAMP
        ''', (ot_id, tipo, incluir, estado))
    
    conn.commit()
    conn.close()
    
    flash('✅ Documentos seleccionados actualizados', 'success')
    return redirect(url_for('ver_ot', ot_id=ot_id))

# ==================== FORMATO 1: ORDEN DE TRABAJO ====================
@app.route('/formato_ot/<int:ot_id>', methods=['GET', 'POST'])
def formato_ot(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    ot = conn.execute('SELECT * FROM ordenes_trabajo WHERE id=?', (ot_id,)).fetchone()
    
    if not ot:
        flash('❌ OT no encontrada', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    # Validar acceso
    if session['usuario_rol'] == 'EJECUTOR' and ot['ejecutor_id'] != session['usuario_id']:
        flash('❌ No tienes acceso a esta OT', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    if request.method == 'POST':
        # Actualizar campos de la OT
        conn.execute('''
            UPDATE ordenes_trabajo 
            SET mttr_objetivo=?, evento_origen=?, solicitado_por=?, aprobado_por=?,
                descripcion_falla=?, sintomas_alarmas=?, actividades_ejecutar=?,
                estado='EN_CURSO'
            WHERE id=?
        ''', (
            request.form.get('mttr_objetivo'), request.form.get('evento_origen'),
            request.form.get('solicitado_por'), request.form.get('aprobado_por'),
            request.form.get('descripcion_falla'), request.form.get('sintomas_alarmas'),
            request.form.get('actividades_ejecutar'), ot_id
        ))
        
        # Guardar personal
        conn.execute('DELETE FROM ot_personal WHERE ot_id=?', (ot_id,))
        nombres = request.form.getlist('personal_nombre[]')
        for i in range(len(nombres)):
            if nombres[i]:
                conn.execute('''
                    INSERT INTO ot_personal (ot_id, nombre, cargo, cedula, ast_firmada, permiso_electrico, hora_inicio)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (ot_id, nombres[i], 
                      request.form.getlist('personal_cargo[]')[i] if i < len(request.form.getlist('personal_cargo[]')) else '',
                      request.form.getlist('personal_cedula[]')[i] if i < len(request.form.getlist('personal_cedula[]')) else '',
                      request.form.getlist('personal_ast[]')[i] if i < len(request.form.getlist('personal_ast[]')) else 'NO',
                      request.form.getlist('personal_permiso[]')[i] if i < len(request.form.getlist('personal_permiso[]')) else 'NO',
                      request.form.getlist('personal_hora[]')[i] if i < len(request.form.getlist('personal_hora[]')) else None))
        
        # Guardar materiales
        conn.execute('DELETE FROM ot_materiales WHERE ot_id=?', (ot_id,))
        items = request.form.getlist('material_item[]')
        for i in range(len(items)):
            if items[i]:
                conn.execute('''
                    INSERT INTO ot_materiales (ot_id, item_material, unidad, cantidad)
                    VALUES (?, ?, ?, ?)
                ''', (ot_id, items[i], 
                      request.form.getlist('material_unidad[]')[i] if i < len(request.form.getlist('material_unidad[]')) else '',
                      request.form.getlist('material_cantidad[]')[i] if i < len(request.form.getlist('material_cantidad[]')) else 0))
        
        # Guardar ejecución
        conn.execute('DELETE FROM ot_ejecucion WHERE ot_id=?', (ot_id,))
        actividades = request.form.getlist('ejecucion_actividad[]')
        for i in range(len(actividades)):
            if actividades[i]:
                conn.execute('''
                    INSERT INTO ot_ejecucion (ot_id, actividad, hora_inicio, hora_fin, ejecuto, resultado_observacion)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (ot_id, actividades[i],
                      request.form.getlist('ejecucion_hora_inicio[]')[i] if i < len(request.form.getlist('ejecucion_hora_inicio[]')) else None,
                      request.form.getlist('ejecucion_hora_fin[]')[i] if i < len(request.form.getlist('ejecucion_hora_fin[]')) else None,
                      request.form.getlist('ejecucion_ejecuto[]')[i] if i < len(request.form.getlist('ejecucion_ejecuto[]')) else '',
                      request.form.getlist('ejecucion_resultado[]')[i] if i < len(request.form.getlist('ejecucion_resultado[]')) else ''))
        
        conn.commit()
        conn.close()
        
        flash('✅ Orden de Trabajo guardada y enviada para revisión', 'success')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    personal = conn.execute('SELECT * FROM ot_personal WHERE ot_id=?', (ot_id,)).fetchall()
    materiales = conn.execute('SELECT * FROM ot_materiales WHERE ot_id=?', (ot_id,)).fetchall()
    ejecucion = conn.execute('SELECT * FROM ot_ejecucion WHERE ot_id=?', (ot_id,)).fetchall()
    conn.close()
    
    return render_template('formato_ot.html', ot=ot, personal=personal, 
                          materiales=materiales, ejecucion=ejecucion)

# ==================== FORMATO 2: INFORME DE FALLA ====================
@app.route('/formato_informe_falla/<int:ot_id>', methods=['GET', 'POST'])
def formato_informe_falla(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    ot = conn.execute('SELECT * FROM ordenes_trabajo WHERE id=?', (ot_id,)).fetchone()
    
    # Validar acceso
    if session['usuario_rol'] == 'EJECUTOR' and ot['ejecutor_id'] != session['usuario_id']:
        flash('❌ No tienes acceso a esta OT', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    if request.method == 'POST':
        # ✅ FIX: Manejar clasificación de falla como checkbox múltiple
        clasificacion_lista = request.form.getlist('clasificacion_falla[]')
        clasificacion_texto = ', '.join(clasificacion_lista) if clasificacion_lista else ''
        
        # ✅ FIX: Manejar checkboxes de causa raíz
        causa_desgaste = 'SI' if request.form.get('causa_raiz_desgaste') else 'NO'
        causa_vandalismo = 'SI' if request.form.get('causa_raiz_vandalismo') else 'NO'
        causa_config = 'SI' if request.form.get('causa_raiz_configuracion') else 'NO'
        
        # ✅ FIX: Todos los campos con .get() para evitar KeyError
        conn.execute('''
            INSERT OR REPLACE INTO informe_falla 
            (ot_id, fecha_deteccion, hora_deteccion, prioridad, detectado_por,
             cargo_detecto, turno, impacto_scada, alarmas_nms, potencia_rx,
             ber, rssi, latencia, clasificacion_falla, diagnostico_inicial,
             herramientas_usadas, acciones_correctivas, potencia_rx_post,
             ber_post, rssi_post, latencia_post, materiales_repuestos,
             requirio_campo, tecnicos_desplazados, hora_deteccion_alarma,
             hora_notificacion_coordinador, hora_inicio_intervencion,
             hora_normalizacion, tiempo_total_respuesta, tiempo_indisponibilidad,
             causa_raiz_desgaste, causa_raiz_vandalismo, causa_raiz_configuracion,
             causa_raiz_otro, descripcion_causa_raiz, ejecutor_firma,
             coordinador_firma, fecha_firma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ot_id,
            request.form.get('fecha_deteccion'),
            request.form.get('hora_deteccion'),
            request.form.get('prioridad'),
            request.form.get('detectado_por'),
            request.form.get('cargo_detecto'),
            request.form.get('turno'),
            request.form.get('impacto_scada'),
            request.form.get('alarmas_nms', ''),
            request.form.get('potencia_rx') or None,
            request.form.get('ber') or None,
            request.form.get('rssi') or None,
            request.form.get('latencia') or None,
            clasificacion_texto,  # ✅ FIX: texto concatenado
            request.form.get('diagnostico_inicial', ''),
            request.form.get('herramientas_usadas', ''),
            request.form.get('acciones_correctivas', ''),
            request.form.get('potencia_rx_post') or None,
            request.form.get('ber_post') or None,
            request.form.get('rssi_post') or None,
            request.form.get('latencia_post') or None,
            request.form.get('materiales_repuestos', ''),
            request.form.get('requirio_campo', 'NO'),
            request.form.get('tecnicos_desplazados', ''),  # ✅ FIX
            request.form.get('hora_deteccion_alarma') or None,
            request.form.get('hora_notificacion_coordinador') or None,
            request.form.get('hora_inicio_intervencion') or None,
            request.form.get('hora_normalizacion') or None,
            request.form.get('tiempo_total_respuesta') or None,
            request.form.get('tiempo_indisponibilidad') or None,
            causa_desgaste,   # ✅ FIX
            causa_vandalismo, # ✅ FIX
            causa_config,     # ✅ FIX
            request.form.get('causa_raiz_otro', ''),
            request.form.get('descripcion_causa_raiz', ''),
            request.form.get('ejecutor_firma', ''),
            request.form.get('coordinador_firma', ''),
            request.form.get('fecha_firma')
        ))
        
        conn.commit()
        conn.close()
        
        flash('✅ Informe de Falla guardado', 'success')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    informe = conn.execute('SELECT * FROM informe_falla WHERE ot_id=?', (ot_id,)).fetchone()
    conn.close()
    
    return render_template('formato_informe_falla.html', ot=ot, informe=informe)

# ==================== FORMATO 3: CERTIFICACIÓN FIBRA ÓPTICA ====================
@app.route('/formato_certificacion/<int:ot_id>', methods=['GET', 'POST'])
def formato_certificacion(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    ot = conn.execute('SELECT * FROM ordenes_trabajo WHERE id=?', (ot_id,)).fetchone()
    
    # Validar acceso
    if session['usuario_rol'] == 'EJECUTOR' and ot['ejecutor_id'] != session['usuario_id']:
        flash('❌ No tienes acceso a esta OT', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    if request.method == 'POST':
        # Verificar si ya existe la certificación
        existente = conn.execute('SELECT id FROM certificacion_fibra WHERE ot_id=?', (ot_id,)).fetchone()
        
        if existente:
            # UPDATE en lugar de INSERT OR REPLACE
            conn.execute('''
                UPDATE certificacion_fibra 
                SET fecha_prueba=?, tecnico_certificador=?, equipo_otdr=?, enlace_tramo=?,
                    origen=?, destino=?, longitud_total=?, tipo_fibra=?, longitud_onda=?,
                    num_fibras_cable=?, num_fibras_certificadas=?, calibracion_otdr=?,
                    resultado_general=?, archivo_reflectograma=?, observaciones_recomendaciones=?,
                    tecnico_firma=?, coordinador_firma=?, director_operacion_firma=?, fecha_firma=?
                WHERE ot_id=?
            ''', (
                request.form.get('fecha_prueba'), request.form.get('tecnico_certificador'),
                request.form.get('equipo_otdr'), request.form.get('enlace_tramo'),
                request.form.get('origen'), request.form.get('destino'), 
                request.form.get('longitud_total'), request.form.get('tipo_fibra'),
                request.form.get('longitud_onda'), request.form.get('num_fibras_cable'),
                request.form.get('num_fibras_certificadas'), request.form.get('calibracion_otdr'),
                request.form.get('resultado_general'), request.form.get('archivo_reflectograma'),
                request.form.get('observaciones_recomendaciones'), request.form.get('tecnico_firma'),
                request.form.get('coordinador_firma'), request.form.get('director_operacion_firma'),
                request.form.get('fecha_firma'), ot_id
            ))
            cert_id = existente['id']
        else:
            # INSERT solo la primera vez
            conn.execute('''
                INSERT INTO certificacion_fibra 
                (ot_id, fecha_prueba, tecnico_certificador, equipo_otdr, enlace_tramo,
                 origen, destino, longitud_total, tipo_fibra, longitud_onda,
                 num_fibras_cable, num_fibras_certificadas, calibracion_otdr,
                 resultado_general, archivo_reflectograma, observaciones_recomendaciones,
                 tecnico_firma, coordinador_firma, director_operacion_firma, fecha_firma)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ot_id, request.form.get('fecha_prueba'), request.form.get('tecnico_certificador'),
                request.form.get('equipo_otdr'), request.form.get('enlace_tramo'),
                request.form.get('origen'), request.form.get('destino'), 
                request.form.get('longitud_total'), request.form.get('tipo_fibra'),
                request.form.get('longitud_onda'), request.form.get('num_fibras_cable'),
                request.form.get('num_fibras_certificadas'), request.form.get('calibracion_otdr'),
                request.form.get('resultado_general'), request.form.get('archivo_reflectograma'),
                request.form.get('observaciones_recomendaciones'), request.form.get('tecnico_firma'),
                request.form.get('coordinador_firma'), request.form.get('director_operacion_firma'),
                request.form.get('fecha_firma')
            ))
            cert_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Guardar resultados OTDR (borrar y recrear solo las filas hijas)
        conn.execute('DELETE FROM certificacion_otdr WHERE certificacion_id=?', (cert_id,))
        fibras = request.form.getlist('otdr_num_fibra[]')
        
        for i in range(len(fibras)):
            if fibras[i]:
                conn.execute('''
                    INSERT INTO certificacion_otdr 
                    (certificacion_id, num_fibra, extremo_ab_atenuacion, extremo_ba_atenuacion,
                     promedio_atenuacion, perdida_total, umbral_perdida, reflexiones,
                     num_empalmes, perdida_max_empalme, perdida_max_conector, longitud_medida,
                     aprobado, longitud_lanzamiento)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cert_id, fibras[i], 
                      request.form.getlist('otdr_ab[]')[i] if i < len(request.form.getlist('otdr_ab[]')) else None,
                      request.form.getlist('otdr_ba[]')[i] if i < len(request.form.getlist('otdr_ba[]')) else None,
                      request.form.getlist('otdr_promedio[]')[i] if i < len(request.form.getlist('otdr_promedio[]')) else None,
                      request.form.getlist('otdr_perdida[]')[i] if i < len(request.form.getlist('otdr_perdida[]')) else None,
                      request.form.getlist('otdr_umbral[]')[i] if i < len(request.form.getlist('otdr_umbral[]')) else None,
                      request.form.getlist('otdr_reflexiones[]')[i] if i < len(request.form.getlist('otdr_reflexiones[]')) else None,
                      request.form.getlist('otdr_empalmes[]')[i] if i < len(request.form.getlist('otdr_empalmes[]')) else None,
                      request.form.getlist('otdr_max_empalme[]')[i] if i < len(request.form.getlist('otdr_max_empalme[]')) else None,
                      request.form.getlist('otdr_max_conector[]')[i] if i < len(request.form.getlist('otdr_max_conector[]')) else None,
                      request.form.getlist('otdr_longitud[]')[i] if i < len(request.form.getlist('otdr_longitud[]')) else None,
                      request.form.getlist('otdr_aprobado[]')[i] if i < len(request.form.getlist('otdr_aprobado[]')) else 'NO',
                      request.form.getlist('otdr_lanzamiento[]')[i] if i < len(request.form.getlist('otdr_lanzamiento[]')) else None))
        
        # Guardar resultados BERT
        conn.execute('DELETE FROM certificacion_bert WHERE certificacion_id=?', (cert_id,))
        bert_fibras = request.form.getlist('bert_num_fibra[]')
        
        for i in range(len(bert_fibras)):
            if bert_fibras[i]:
                conn.execute('''
                    INSERT INTO certificacion_bert 
                    (certificacion_id, num_fibra, velocidad_prueba, duracion_prueba,
                     bits_transmitidos, bits_con_error, ber_obtenido, ber_umbral,
                     aprobado, observacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cert_id, bert_fibras[i],
                      request.form.getlist('bert_velocidad[]')[i] if i < len(request.form.getlist('bert_velocidad[]')) else None,
                      request.form.getlist('bert_duracion[]')[i] if i < len(request.form.getlist('bert_duracion[]')) else None,
                      request.form.getlist('bert_transmitidos[]')[i] if i < len(request.form.getlist('bert_transmitidos[]')) else None,
                      request.form.getlist('bert_error[]')[i] if i < len(request.form.getlist('bert_error[]')) else None,
                      request.form.getlist('bert_ber[]')[i] if i < len(request.form.getlist('bert_ber[]')) else None,
                      request.form.getlist('bert_umbral[]')[i] if i < len(request.form.getlist('bert_umbral[]')) else None,
                      request.form.getlist('bert_aprobado[]')[i] if i < len(request.form.getlist('bert_aprobado[]')) else 'NO',
                      request.form.getlist('bert_observacion[]')[i] if i < len(request.form.getlist('bert_observacion[]')) else None))
        
        conn.commit()
        conn.close()
        
        flash('✅ Certificación de Fibra Óptica guardada', 'success')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    certificacion = conn.execute(
        'SELECT * FROM certificacion_fibra WHERE ot_id=?', (ot_id,)
    ).fetchone()
    
    otdr_results = []
    bert_results = []
    if certificacion:
        otdr_results = conn.execute(
            'SELECT * FROM certificacion_otdr WHERE certificacion_id=?', 
            (certificacion['id'],)
        ).fetchall()
        bert_results = conn.execute(
            'SELECT * FROM certificacion_bert WHERE certificacion_id=?', 
            (certificacion['id'],)
        ).fetchall()
    
    conn.close()
    
    return render_template('formato_certificacion.html', ot=ot, 
                          certificacion=certificacion,
                          otdr_results=otdr_results, 
                          bert_results=bert_results)

# ==================== FORMATO 4: ACTA DE ENTREGA ====================
@app.route('/formato_acta_entrega/<int:ot_id>', methods=['GET', 'POST'])
def formato_acta_entrega(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    ot = conn.execute('SELECT * FROM ordenes_trabajo WHERE id=?', (ot_id,)).fetchone()
    
    # Validar acceso
    if session['usuario_rol'] == 'EJECUTOR' and ot['ejecutor_id'] != session['usuario_id']:
        flash('❌ No tienes acceso a esta OT', 'danger')
        return redirect(url_for('dashboard_ejecutor'))
    
    if request.method == 'POST':
        conn.execute('''
            INSERT OR REPLACE INTO acta_entrega 
            (ot_id, fecha_entrega, hora_entrega, turno_cce_receptor, activo_entregado,
             tipo_medio, subestacion_nodo, tecnico_entrega, operador_cce_recibe,
             turno_operador, potencia_rx_antes, potencia_rx_despues, ber_antes,
             ber_despues, rssi_antes, rssi_despues, latencia_antes, latencia_despues,
             estado_canal_antes, estado_canal_despues, alarmas_nms_antes,
             alarmas_nms_despues, pruebas_otdr_aprobada, pruebas_bert_aprobada,
             pruebas_potencia_aprobada, pruebas_rssi_aprobada, pruebas_latencia_aprobada,
             pruebas_ping_aprobada, pruebas_comunicacion_aprobada,
             declaracion_normalizacion, ejecutor_firma, recibe_firma,
             valida_coordinador_firma, fecha_firma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ot_id, 
            request.form.get('fecha_entrega'), 
            request.form.get('hora_entrega'),
            request.form.get('turno_cce_receptor', ''), 
            request.form.get('activo_entregado', ''),
            request.form.get('tipo_medio', 'FO'), 
            request.form.get('subestacion_nodo', ''),
            request.form.get('tecnico_entrega', ''), 
            request.form.get('operador_cce_recibe', ''),
            request.form.get('turno_operador', ''), 
            request.form.get('potencia_rx_antes') or None,
            request.form.get('potencia_rx_despues') or None, 
            request.form.get('ber_antes') or None,
            request.form.get('ber_despues') or None, 
            request.form.get('rssi_antes') or None,
            request.form.get('rssi_despues') or None, 
            request.form.get('latencia_antes') or None,
            request.form.get('latencia_despues') or None, 
            request.form.get('estado_canal_antes', ''),
            request.form.get('estado_canal_despues', ''), 
            request.form.get('alarmas_nms_antes', ''),
            request.form.get('alarmas_nms_despues', ''), 
            request.form.get('pruebas_otdr_aprobada', 'NO'),
            request.form.get('pruebas_bert_aprobada', 'NO'),
            request.form.get('pruebas_potencia_aprobada', 'NO'),
            request.form.get('pruebas_rssi_aprobada', 'NO'),
            request.form.get('pruebas_latencia_aprobada', 'NO'),
            request.form.get('pruebas_ping_aprobada', 'NO'),
            request.form.get('pruebas_comunicacion_aprobada', 'NO'),
            request.form.get('declaracion_normalizacion', ''), 
            request.form.get('ejecutor_firma', ''),
            request.form.get('recibe_firma', ''), 
            request.form.get('valida_coordinador_firma', ''),
            request.form.get('fecha_firma')
        ))
        
        conn.commit()
        conn.close()
        
        flash('✅ Acta de Entrega guardada', 'success')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    acta = conn.execute('SELECT * FROM acta_entrega WHERE ot_id=?', (ot_id,)).fetchone()
    conn.close()
    
    return render_template('formato_acta_entrega.html', ot=ot, acta=acta)

# ==================== ENVIAR DOCUMENTO PARA REVISIÓN ====================
@app.route('/enviar_documento/<int:ot_id>/<tipo_documento>', methods=['POST'])
def enviar_documento(ot_id, tipo_documento):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('''
        UPDATE ot_documentos_estado 
        SET estado='ENVIADO', fecha_actualizacion=CURRENT_TIMESTAMP
        WHERE ot_id=? AND tipo_documento=?
    ''', (ot_id, tipo_documento))
    conn.commit()
    conn.close()
    
    flash(f'✅ Documento {tipo_documento} enviado para revisión', 'success')
    return redirect(url_for('ver_ot', ot_id=ot_id))

# ==================== PANEL DE REVISIÓN DEL COORDINADOR ====================
@app.route('/revision_documentos')
def revision_documentos():
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    conn = get_db()
    documentos_enviados = conn.execute('''
        SELECT ode.*, ot.codigo_ot, ot.tipo_ot, u.nombre as ejecutor_nombre
        FROM ot_documentos_estado ode
        JOIN ordenes_trabajo ot ON ot.id = ode.ot_id
        JOIN usuarios u ON u.id = ot.ejecutor_id
        WHERE ode.estado = 'ENVIADO'
        ORDER BY ode.fecha_actualizacion DESC
    ''').fetchall()
    conn.close()
    
    return render_template('revision_documentos.html', documentos=documentos_enviados)

# ==================== APROBAR/DEVOLVER DOCUMENTO ====================
@app.route('/aprobar_documento/<int:ot_id>/<tipo_documento>/<accion>', methods=['POST'])
def aprobar_documento(ot_id, tipo_documento, accion):
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    observaciones = request.form.get('observaciones', '')
    nuevo_estado = 'APROBADO' if accion == 'APROBAR' else 'DEVUELTO'
    
    conn = get_db()
    conn.execute('''
        UPDATE ot_documentos_estado 
        SET estado=?, observaciones=?, fecha_actualizacion=CURRENT_TIMESTAMP
        WHERE ot_id=? AND tipo_documento=?
    ''', (nuevo_estado, observaciones, ot_id, tipo_documento))
    
    # Si se devuelve, cambiar estado de OT a EN_CURSO para que el ejecutor pueda editar
    if accion == 'DEVOLVER':
        conn.execute('UPDATE ordenes_trabajo SET estado="EN_CURSO" WHERE id=?', (ot_id,))
    
    conn.commit()
    conn.close()
    
    flash(f'✅ Documento {nuevo_estado}', 'success')
    return redirect(url_for('revision_documentos'))

# ==================== GESTIONAR EJECUTORES ====================
@app.route('/gestionar_ejecutores', methods=['GET', 'POST'])
def gestionar_ejecutores():
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?, ?, ?, 'EJECUTOR')",
                (username, password, nombre)
            )
            conn.commit()
            flash(f'✅ Ejecutor {nombre} creado exitosamente', 'success')
        except sqlite3.IntegrityError:
            flash('❌ El nombre de usuario ya existe', 'danger')
        conn.close()
        return redirect(url_for('gestionar_ejecutores'))
    
    conn = get_db()
    ejecutores = conn.execute(
        "SELECT * FROM usuarios WHERE rol='EJECUTOR' ORDER BY nombre"
    ).fetchall()
    conn.close()
    
    return render_template('gestionar_ejecutores.html', ejecutores=ejecutores)

@app.route('/toggle_ejecutor/<int:ejecutor_id>')
def toggle_ejecutor(ejecutor_id):
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    conn = get_db()
    ejecutor = conn.execute('SELECT activo FROM usuarios WHERE id=?', (ejecutor_id,)).fetchone()
    nuevo_estado = 0 if ejecutor['activo'] == 1 else 1
    conn.execute('UPDATE usuarios SET activo=? WHERE id=?', (nuevo_estado, ejecutor_id))
    conn.commit()
    conn.close()
    
    flash('✅ Estado del ejecutor actualizado', 'success')
    return redirect(url_for('gestionar_ejecutores'))

# ==================== CERRAR OT ====================
@app.route('/cerrar_ot/<int:ot_id>', methods=['POST'])
def cerrar_ot(ot_id):
    if 'usuario_id' not in session or session['usuario_rol'] != 'COORDINADOR':
        return redirect(url_for('login'))
    
    conn = get_db()
    conn.execute('''
        UPDATE ordenes_trabajo 
        SET estado='CERRADA', fecha_cierre=CURRENT_TIMESTAMP
        WHERE id=?
    ''', (ot_id,))
    conn.commit()
    conn.close()
    
    flash('✅ OT cerrada exitosamente', 'success')
    return redirect(url_for('ver_ot', ot_id=ot_id))

# ==================== CARGA DE EVIDENCIAS ====================
@app.route('/cargar_evidencia/<int:ot_id>', methods=['POST'])
def cargar_evidencia(ot_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if 'archivo' not in request.files:
        flash('❌ No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    archivo = request.files['archivo']
    tipo_documento = request.form.get('tipo_documento', 'OT')
    descripcion = request.form.get('descripcion', '')
    
    if archivo.filename == '':
        flash('❌ No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('ver_ot', ot_id=ot_id))
    
    if archivo:
        filename = secure_filename(f"{ot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(filepath)
        
        conn = get_db()
        conn.execute('''
            INSERT INTO evidencias (ot_id, documento_tipo, ruta_archivo, descripcion)
            VALUES (?, ?, ?, ?)
        ''', (ot_id, tipo_documento, filepath, descripcion))
        conn.commit()
        conn.close()
        
        flash('✅ Evidencia cargada exitosamente', 'success')
    
    return redirect(url_for('ver_ot', ot_id=ot_id))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)