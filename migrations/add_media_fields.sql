-- GestorPro — Migración: campos de imagen y categoría
-- Ejecutar en producción:
-- docker cp add_media_fields.sql servorax-db:/tmp/
-- docker exec -it servorax-db psql -U luigui -d servorax_db -f /tmp/add_media_fields.sql

ALTER TABLE servicios ADD COLUMN IF NOT EXISTS categoria  VARCHAR(100);
ALTER TABLE servicios ADD COLUMN IF NOT EXISTS imagen_url VARCHAR(500);

SELECT '✅ Migración aplicada' as resultado;
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('servicios','barberos')
  AND column_name IN ('categoria','imagen_url','foto_url')
ORDER BY table_name, column_name;
