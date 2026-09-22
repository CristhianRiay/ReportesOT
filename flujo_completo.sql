-- ============================================
-- SIMULACIÓN DEL FLUJO COMPLETO
-- Ejecutar paso a paso para ver cómo evoluciona el sistema
-- ============================================

-- ============================================
-- PASO 1: SOLICITANTE CREA UNA NUEVA OT
-- ============================================

BEGIN TRANSACTION;

-- Insertar la nueva OT
INSERT INTO ordenes_trabajo (
    codigo_ot, estado, solicitante_nombre, solicitante_contacto,
    coordinador_id, resumen_problema, detalle_problema, tipo_falla, prioridad
) VALUES (
    'OT-2026-005', 'NUEVA', 'Juan Pérez', '3001112233',
    1, 'Falla en splitter de caja NAP',
    'Se reporta pérdida de señal en 8 clientes conectados al splitter de la caja NAP-067. Posible daño en el equipo.',
    'FALLA_EQUIPO', 2
);

-- Obtener el ID de la OT recién creada
SET @nueva_ot_id = last_insert_rowid();

-- Generar alarma automática al coordinador
INSERT INTO alarmas (ot_id, coordinador_id, estado, tipo_alarma, mensaje) VALUES
(@nueva_ot_id, 1, 'PENDIENTE', 'NUEVA_OT', 
 'Nueva OT creada: Falla en splitter de caja NAP - Prioridad MEDIA');

COMMIT;

-- Verificar
SELECT '✅ PASO 1 COMPLETADO: OT creada y alarma generada' AS estado;
SELECT * FROM vw_ot_resumen WHERE codigo_ot = 'OT-2026-005';
SELECT * FROM vw_alarmas_pendientes WHERE codigo_ot = 'OT-2026-005';


-- ============================================
-- PASO 2: COORDINADOR RECIBE ALARMA Y ASIGNA
-- ============================================

BEGIN TRANSACTION;

-- Coordinador lee la alarma
UPDATE alarmas 
SET estado = 'LEIDA', fecha_procesamiento = CURRENT_TIMESTAMP
WHERE ot_id = 5 AND coordinador_id = 1;

-- Asignar cuadrilla a la OT
UPDATE ordenes_trabajo 
SET 
    estado = 'ASIGNADA',
    cuadrilla_id = 1,
    fecha_asignacion = CURRENT_TIMESTAMP
WHERE id = 5;

-- Actualizar alarma a asignada
UPDATE alarmas 
SET estado = 'ASIGNADA'
WHERE ot_id = 5;

COMMIT;

-- Verificar
SELECT '✅ PASO 2 COMPLETADO: OT asignada a cuadrilla' AS estado;
SELECT * FROM vw_ot_resumen WHERE codigo_ot = 'OT-2026-005';


-- ============================================
-- PASO 3: CUADRILLA ACEPTA LA OT
-- ============================================

BEGIN TRANSACTION;

-- Cuadrilla acepta la orden
INSERT INTO recepciones_cuadrilla (ot_id, cuadrilla_id, accion, observaciones) VALUES
(5, 1, 'ACEPTA', 'Cuadrilla en camino al sitio. Tiempo estimado de llegada: 30 minutos.');

-- Actualizar estado de la OT
UPDATE ordenes_trabajo 
SET estado = 'EN_EJECUCION', fecha_inicio_ejecucion = CURRENT_TIMESTAMP
WHERE id = 5;

COMMIT;

-- Verificar
SELECT '✅ PASO 3 COMPLETADO: Cuadrilla aceptó y está en ejecución' AS estado;
SELECT * FROM vw_ot_resumen WHERE codigo_ot = 'OT-2026-005';
SELECT * FROM recepciones_cuadrilla WHERE ot_id = 5;


-- ============================================
-- PASO 4: CUADRILLA EJECUTA Y CARGA EVIDENCIA
-- ============================================

BEGIN TRANSACTION;

-- Cargar evidencias
INSERT INTO evidencia_ot (ot_id, tipo_evidencia, url_archivo, nombre_archivo, descripcion) VALUES
(5, 'FOTO', '/uploads/ot5/splitter_danado.jpg', 'splitter_danado.jpg', 'Splitter dañado en caja NAP-067'),
(5, 'FOTO', '/uploads/ot5/splitter_nuevo.jpg', 'splitter_nuevo.jpg', 'Splitter nuevo instalado y conectado'),
(5, 'FOTO', '/uploads/ot5/prueba_senal.jpg', 'prueba_senal.jpg', 'Prueba de señal con OTDR - niveles OK');

COMMIT;

-- Verificar
SELECT '✅ PASO 4 COMPLETADO: Evidencia cargada' AS estado;
SELECT * FROM evidencia_ot WHERE ot_id = 5;


-- ============================================
-- PASO 5: CUADRILLA REGISTRA MATERIALES CONSUMIDOS
-- ============================================

BEGIN TRANSACTION;

-- Registrar materiales consumidos
INSERT INTO materiales_consumidos (ot_id, material_id, cantidad, unidad, nota) VALUES
(5, 6, 1, 'unidad', 'Splitter 1:8 - reemplazo del equipo dañado'),
(5, 2, 4, 'unidad', 'Conectores SC/APC para reconexión de clientes'),
(5, 4, 4, 'unidad', 'Tubos termorretráctiles para protección de empalmes');

-- Actualizar inventario (descuento de stock)
-- Splitter 1:8 (id=6): stock anterior 40, nuevo 39
UPDATE materiales 
SET stock_actual = stock_actual - 1, fecha_actualizacion = CURRENT_TIMESTAMP
WHERE id = 6;

-- Conectores SC/APC (id=2): stock anterior 200, nuevo 196
UPDATE materiales 
SET stock_actual = stock_actual - 4, fecha_actualizacion = CURRENT_TIMESTAMP
WHERE id = 2;

-- Tubos termorretráctiles (id=4): stock anterior 100, nuevo 96
UPDATE materiales 
SET stock_actual = stock_actual - 4, fecha_actualizacion = CURRENT_TIMESTAMP
WHERE id = 4;

-- Registrar movimientos de inventario
INSERT INTO movimientos_inventario (material_id, ot_id, tipo_movimiento, cantidad, cantidad_anterior, cantidad_nueva, motivo) VALUES
(6, 5, 'CONSUMO', 1, 40, 39, 'Consumo en OT-2026-005 - Reemplazo splitter'),
(2, 5, 'CONSUMO', 4, 200, 196, 'Consumo en OT-2026-005 - Reconexión clientes'),
(4, 5, 'CONSUMO', 4, 100, 96, 'Consumo en OT-2026-005 - Protección empalmes');

COMMIT;

-- Verificar
SELECT '✅ PASO 5 COMPLETADO: Materiales consumidos y stock actualizado' AS estado;
SELECT * FROM materiales_consumidos WHERE ot_id = 5;
SELECT * FROM vw_inventario WHERE codigo IN ('EQU-002', 'FIB-002', 'FIB-004');


-- ============================================
-- PASO 6: COORDINADOR CIERRA LA OT
-- ============================================

BEGIN TRANSACTION;

-- Coordinador revisa y cierra
UPDATE ordenes_trabajo 
SET 
    estado = 'CERRADA',
    fecha_cierre = CURRENT_TIMESTAMP,
    observaciones_cierre = 'Splitter reemplazado exitosamente. Señel restablecida en los 8 clientes. Pruebas de OTDR dentro de parámetros.'
WHERE id = 5;

COMMIT;

-- Verificar
SELECT '✅ PASO 6 COMPLETADO: OT cerrada exitosamente' AS estado;
SELECT * FROM vw_ot_resumen WHERE codigo_ot = 'OT-2026-005';


-- ============================================
-- RESUMEN FINAL
-- ============================================

SELECT '========================================' AS '';
SELECT 'RESUMEN DEL SISTEMA' AS '';
SELECT '========================================' AS '';

SELECT 'Órdenes de trabajo por estado:' AS '';
SELECT estado, COUNT(*) AS cantidad FROM ordenes_trabajo GROUP BY estado;

SELECT 'Alarmas pendientes:' AS '';
SELECT COUNT(*) AS alarmas_pendientes FROM alarmas WHERE estado = 'PENDIENTE';

SELECT 'Materiales con stock bajo:' AS '';
SELECT codigo, nombre, stock_actual, stock_minimo 
FROM materiales 
WHERE stock_actual <= stock_minimo AND activo = 1;

SELECT 'Total de movimientos de inventario:' AS '';
SELECT COUNT(*) AS total_movimientos FROM movimientos_inventario;