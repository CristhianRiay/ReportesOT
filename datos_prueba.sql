-- Usuarios (Contraseñas en texto plano para desarrollo local)
INSERT INTO usuarios (username, password, nombre, rol) VALUES
('coordinador', 'admin123', 'Carlos Coordinador', 'COORDINADOR'),
('ejecutor', 'ejecutor123', 'Juan Ejecutor', 'EJECUTOR'),
('ejecutor2', 'ejecutor123', 'Pedro Técnico', 'EJECUTOR');

-- OT de prueba
INSERT INTO ordenes_trabajo (
    codigo_ot, tipo_ot, prioridad, activo_canal_afectado, subestacion_nodo,
    medio, sistema_scada_afectado, fecha_creacion, hora_creacion,
    descripcion_falla, ejecutor_id, estado
) VALUES (
    'OT-COM-001', 'CORRECTIVA', 'ALTA', 'Canal SE-Norte', 'Subestación Norte',
    'FO', 'SI', '2026-09-10', '08:30:00',
    'Pérdida de señal en enlace de fibra óptica principal', 2, 'ASIGNADA'
);

-- Estado inicial de documentos para la OT de prueba
INSERT INTO ot_documentos_estado (ot_id, tipo_documento, incluir, estado) VALUES
(1, 'OT', 1, 'PENDIENTE'),
(1, 'INFORME_FALLA', 1, 'PENDIENTE'),
(1, 'CERTIFICACION', 1, 'PENDIENTE'),
(1, 'ACTA_ENTREGA', 1, 'PENDIENTE');