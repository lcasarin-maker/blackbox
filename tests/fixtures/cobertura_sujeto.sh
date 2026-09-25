#!/usr/bin/env bash
# Sujeto de prueba de tools/cobertura_bash.sh. Los numeros de linea IMPORTAN:
# tests/test_cobertura_bash.py los cita. No reordenar sin actualizarlo.
llamada_directa() {
  local a=1          # L5
  echo "$a"          # L6
}
llamada_en_substitucion() {
  local b=2          # L9  -- corre a profundidad 2 de xtrace
  echo "$b"          # L10
}
nunca_llamada() {
  local c=3          # L13 -- tiene que salir SIN CUBRIR
  echo "$c"          # L14
}
llamada_directa >/dev/null
z=$(llamada_en_substitucion)
echo "z=$z"
