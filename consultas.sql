-- ============================================
-- CONSULTAS ÚTILES PARA VISUALIZAR EL SISTEMA
-- ============================================

-- 1. Dashboard de órdenes de trabajo
SELECT 
    estado,
    COUNT(*) AS total,
    GROUP_CONCAT(codigo_ot) AS ordenes
FROM ordenes_trabajo
GROUP BY estado;

-- 2. Panel del coordinador: alarmas pendientes
SELECT 
    a.ot_id,
    ot.codigo_ot,
    ot.resumen_problema,
    ot.prioridad,
    a.fecha_creacion,
    ROUND((julianday('now') - julianday(a.fecha_creacion)) * 60, 0) AS minutos_pendiente
FROM alarmas a
JOIN ordenes_trabajo ot ON ot.id = a.ot_id
WHERE a.estado = 'PENDIENTE'
ORDER BY ot.prioridad ASC, a.fecha_creacion ASC;

-- 3. Inventario actual con alertas
SELECT 
    codigo,
    nombre,
    stock_actual,
    stock_minimo,
    CASE 
        WHEN stock_actual = 0 THEN '🔴 Agotado'
        WHEN stock_actual <= stock_minimo THEN '️ Stock bajo'
        ELSE '✅ OK'
    END AS estado,
    precio_unitario
FROM materiales
WHERE activo = 1
ORDER BY 
    CASE 
        WHEN stock_actual = 0 THEN 1
        WHEN stock_actual <= stock_minimo THEN 2
        ELSE 3
    END,
    nombre;

-- 4. Detalle completo de una OT específica
SELECT 
    ot.codigo_ot,
    ot.estado,
    ot.solicitante_nombre,
    c.nombre AS coordinador,
    q.nombre AS cuadrilla,
    ot.resumen_problema,
    ot.detalle_problema,
    ot.prioridad,
    ot.fecha_creacion,
    ot.fecha_asignacion,
    ot.fecha_inicio_ejecucion,
    ot.fecha_cierre,
    ot.observaciones_cierre
FROM ordenes_trabajo ot
LEFT JOIN coordinadores c ON c.id = ot.coordinador_id
LEFT JOIN cuadrillas q ON q.id = ot.cuadrilla_id
WHERE ot.id = 5;

-- 5. Materiales consumidos en una OT
SELECT 
    m.codigo,
    m.nombre,
    mc.cantidad,
    mc.unidad,
    mc.nota
FROM materiales_consumidos mc
JOIN materiales m ON m.id = mc.material_id
WHERE mc.ot_id = 5;

-- 6. Historial de movimientos de inventario
SELECT 
    m.codigo,
    m.nombre,
    mi.tipo_movimiento,
    mi.cantidad,
    mi.cantidad_anterior,
    mi.cantidad_nueva,
    mi.fecha,
    mi.motivo
FROM movimientos_inventario mi
JOIN materiales m ON m.id = mi.material_id
ORDER BY mi.fecha DESC
LIMIT 20;

-- 7. Evidencia de una OT
SELECT 
    tipo_evidencia,
    nombre_archivo,
    descripcion,
    fecha_carga
FROM evidencia_ot
WHERE ot_id = 5;

-- 8. Rendimiento de cuadrillas
SELECT 
    q.nombre AS cuadrilla,
    COUNT(ot.id) AS total_ot,
    SUM(CASE WHEN ot.estado = 'CERRADA' THEN 1 ELSE 0 END) AS cerradas,
    SUM(CASE WHEN ot.estado = 'EN_EJECUCION' THEN 1 ELSE 0 END) AS en_ejecucion,
    SUM(CASE WHEN ot.estado = 'RECHAZADA' THEN 1 ELSE 0 END) AS rechazadas
FROM cuadrillas q
LEFT JOIN ordenes_trabajo ot ON ot.cuadrilla_id = q.id
GROUP BY q.id, q.nombre;