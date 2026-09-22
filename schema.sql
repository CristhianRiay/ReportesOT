PRAGMA foreign_keys = ON;

-- 1. USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL CHECK(rol IN ('COORDINADOR', 'EJECUTOR')),
    activo INTEGER DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ÓRDENES DE TRABAJO
CREATE TABLE IF NOT EXISTS ordenes_trabajo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_ot TEXT UNIQUE NOT NULL,
    tipo_ot TEXT CHECK(tipo_ot IN ('CORRECTIVA', 'PREVENTIVA', 'MODIFICATIVA')),
    prioridad TEXT CHECK(prioridad IN ('URGENTE', 'ALTA', 'NORMAL', 'BAJA')),
    estado TEXT DEFAULT 'ASIGNADA' CHECK(estado IN ('ASIGNADA', 'EN_CURSO', 'CERRADA')),
    activo_canal_afectado TEXT,
    subestacion_nodo TEXT,
    medio TEXT CHECK(medio IN ('FO', 'GPRS', 'AMBOS')),
    sistema_scada_afectado TEXT CHECK(sistema_scada_afectado IN ('SI', 'NO', 'PARCIAL')),
    fecha_creacion DATE,
    hora_creacion TIME,
    fecha_requerida DATE,
    mttr_objetivo TEXT,
    evento_origen TEXT,
    solicitado_por TEXT,
    aprobado_por TEXT,
    descripcion_falla TEXT,
    sintomas_alarmas TEXT,
    actividades_ejecutar TEXT,
    ejecutor_id INTEGER,
    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP,
    FOREIGN KEY (ejecutor_id) REFERENCES usuarios(id)
);

-- 3. PERSONAL ASIGNADO A OT
CREATE TABLE IF NOT EXISTS ot_personal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL,
    nombre TEXT, cargo TEXT, cedula TEXT,
    ast_firmada TEXT CHECK(ast_firmada IN ('SI', 'NO')),
    permiso_electrico TEXT CHECK(permiso_electrico IN ('SI', 'NO')),
    hora_inicio TIME,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 4. MATERIALES DE OT
CREATE TABLE IF NOT EXISTS ot_materiales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL,
    item_material TEXT, unidad TEXT, cantidad REAL,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 5. REGISTRO DE EJECUCIÓN
CREATE TABLE IF NOT EXISTS ot_ejecucion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL,
    actividad TEXT, hora_inicio TIME, hora_fin TIME, ejecuto TEXT, resultado_observacion TEXT,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 6. INFORME DE FALLA
CREATE TABLE IF NOT EXISTS informe_falla (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER UNIQUE NOT NULL,
    fecha_deteccion DATE, hora_deteccion TIME,
    prioridad TEXT CHECK(prioridad IN ('CRITICA', 'MAYOR', 'MENOR')),
    detectado_por TEXT, cargo_detecto TEXT, turno TEXT,
    impacto_scada TEXT CHECK(impacto_scada IN ('PARCIAL', 'TOTAL', 'SIN_IMPACTO')),
    alarmas_nms TEXT,
    potencia_rx REAL, ber REAL, rssi REAL, latencia INTEGER,
    clasificacion_falla TEXT, diagnostico_inicial TEXT, herramientas_usadas TEXT, acciones_correctivas TEXT,
    potencia_rx_post REAL, ber_post REAL, rssi_post REAL, latencia_post INTEGER,
    materiales_repuestos TEXT, requirio_campo TEXT CHECK(requirio_campo IN ('SI', 'NO')), tecnicos_desplazados TEXT,
    hora_deteccion_alarma TIME, hora_notificacion_coordinador TIME, hora_inicio_intervencion TIME, hora_normalizacion TIME,
    tiempo_total_respuesta INTEGER, tiempo_indisponibilidad INTEGER,
    causa_raiz_desgaste TEXT, causa_raiz_vandalismo TEXT, causa_raiz_configuracion TEXT, causa_raiz_otro TEXT, descripcion_causa_raiz TEXT,
    ejecutor_firma TEXT, coordinador_firma TEXT, fecha_firma DATE,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 7. CERTIFICACIÓN FIBRA ÓPTICA
CREATE TABLE IF NOT EXISTS certificacion_fibra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER UNIQUE NOT NULL,
    fecha_prueba DATE, tecnico_certificador TEXT, equipo_otdr TEXT, enlace_tramo TEXT,
    origen TEXT, destino TEXT, longitud_total REAL,
    tipo_fibra TEXT CHECK(tipo_fibra IN ('SM_G652D', 'G657', 'MM_OM3')),
    longitud_onda TEXT CHECK(longitud_onda IN ('1310', '1550')),
    num_fibras_cable INTEGER, num_fibras_certificadas INTEGER,
    calibracion_otdr TEXT CHECK(calibracion_otdr IN ('VIGENTE', 'VENCIDA')),
    resultado_general TEXT CHECK(resultado_general IN ('APROBADO', 'RECHAZADO', 'CONDICIONADO')),
    archivo_reflectograma TEXT, observaciones_recomendaciones TEXT,
    tecnico_firma TEXT, coordinador_firma TEXT, director_operacion_firma TEXT, fecha_firma DATE,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 8. RESULTADOS OTDR
CREATE TABLE IF NOT EXISTS certificacion_otdr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificacion_id INTEGER NOT NULL,
    num_fibra INTEGER,
    extremo_ab_atenuacion REAL, extremo_ba_atenuacion REAL, promedio_atenuacion REAL,
    perdida_total REAL, umbral_perdida REAL, reflexiones REAL,
    num_empalmes INTEGER, perdida_max_empalme REAL, perdida_max_conector REAL, longitud_medida REAL,
    aprobado TEXT CHECK(aprobado IN ('SI', 'NO')), longitud_lanzamiento INTEGER,
    FOREIGN KEY (certificacion_id) REFERENCES certificacion_fibra(id) ON DELETE CASCADE
);

-- 9. RESULTADOS BERT
CREATE TABLE IF NOT EXISTS certificacion_bert (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificacion_id INTEGER NOT NULL,
    num_fibra INTEGER, velocidad_prueba INTEGER, duracion_prueba INTEGER,
    bits_transmitidos INTEGER, bits_con_error INTEGER, ber_obtenido REAL, ber_umbral REAL,
    aprobado TEXT CHECK(aprobado IN ('SI', 'NO')), observacion TEXT,
    FOREIGN KEY (certificacion_id) REFERENCES certificacion_fibra(id) ON DELETE CASCADE
);

-- 10. ACTA DE ENTREGA
CREATE TABLE IF NOT EXISTS acta_entrega (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER UNIQUE NOT NULL,
    fecha_entrega DATE, hora_entrega TIME, turno_cce_receptor TEXT, activo_entregado TEXT,
    tipo_medio TEXT CHECK(tipo_medio IN ('FO', 'GPRS', 'AMBOS')), subestacion_nodo TEXT,
    tecnico_entrega TEXT, operador_cce_recibe TEXT, turno_operador TEXT,
    potencia_rx_antes REAL, potencia_rx_despues REAL, ber_antes REAL, ber_despues REAL,
    rssi_antes REAL, rssi_despues REAL, latencia_antes INTEGER, latencia_despues INTEGER,
    estado_canal_antes TEXT, estado_canal_despues TEXT, alarmas_nms_antes TEXT, alarmas_nms_despues TEXT,
    pruebas_otdr_aprobada TEXT, pruebas_bert_aprobada TEXT, pruebas_potencia_aprobada TEXT,
    pruebas_rssi_aprobada TEXT, pruebas_latencia_aprobada TEXT, pruebas_ping_aprobada TEXT, pruebas_comunicacion_aprobada TEXT,
    declaracion_normalizacion TEXT, ejecutor_firma TEXT, recibe_firma TEXT, valida_coordinador_firma TEXT, fecha_firma DATE,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 11. EVIDENCIAS
CREATE TABLE IF NOT EXISTS evidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL,
    documento_tipo TEXT CHECK(documento_tipo IN ('OT', 'INFORME_FALLA', 'CERTIFICACION', 'ACTA_ENTREGA')),
    ruta_archivo TEXT, descripcion TEXT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE
);

-- 12. ESTADO DE DOCUMENTOS (NUEVA - Para el flujo de revisión y selección)
CREATE TABLE IF NOT EXISTS ot_documentos_estado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ot_id INTEGER NOT NULL,
    tipo_documento TEXT NOT NULL CHECK(tipo_documento IN ('OT', 'INFORME_FALLA', 'CERTIFICACION', 'ACTA_ENTREGA')),
    incluir INTEGER NOT NULL DEFAULT 1,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK(estado IN ('PENDIENTE', 'EN_PROGRESO', 'ENVIADO', 'APROBADO', 'DEVUELTO', 'NO_APLICA')),
    observaciones TEXT,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ot_id) REFERENCES ordenes_trabajo(id) ON DELETE CASCADE,
    UNIQUE(ot_id, tipo_documento)
);

-- ==================== VISTAS ====================

CREATE VIEW IF NOT EXISTS vw_ot_resumen AS
SELECT 
    ot.id, ot.codigo_ot, ot.tipo_ot, ot.prioridad, ot.estado,
    ot.activo_canal_afectado, ot.subestacion_nodo, ot.fecha_creacion, ot.fecha_asignacion,
    ot.ejecutor_id, u.nombre as ejecutor_nombre
FROM ordenes_trabajo ot
LEFT JOIN usuarios u ON ot.ejecutor_id = u.id
ORDER BY ot.fecha_creacion DESC;

CREATE VIEW IF NOT EXISTS vw_estado_documentos AS
SELECT 
    ot.id as ot_id, ot.codigo_ot,
    COALESCE(ode_ot.incluir, 1) as ot_incluir, COALESCE(ode_ot.estado, 'PENDIENTE') as ot_estado,
    COALESCE(ode_if.incluir, 1) as informe_incluir, COALESCE(ode_if.estado, 'PENDIENTE') as informe_estado,
    COALESCE(ode_cf.incluir, 1) as cert_incluir, COALESCE(ode_cf.estado, 'PENDIENTE') as cert_estado,
    COALESCE(ode_ae.incluir, 1) as acta_incluir, COALESCE(ode_ae.estado, 'PENDIENTE') as acta_estado
FROM ordenes_trabajo ot
LEFT JOIN ot_documentos_estado ode_ot ON ot.id = ode_ot.ot_id AND ode_ot.tipo_documento = 'OT'
LEFT JOIN ot_documentos_estado ode_if ON ot.id = ode_if.ot_id AND ode_if.tipo_documento = 'INFORME_FALLA'
LEFT JOIN ot_documentos_estado ode_cf ON ot.id = ode_cf.ot_id AND ode_cf.tipo_documento = 'CERTIFICACION'
LEFT JOIN ot_documentos_estado ode_ae ON ot.id = ode_ae.ot_id AND ode_ae.tipo_documento = 'ACTA_ENTREGA';