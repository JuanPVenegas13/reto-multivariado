#!/usr/bin/env bash
set -euo pipefail

## Ejecutar siempre desde la raíz del repositorio,
## sin importar desde dónde se invoque el script
cd "$(git rev-parse --show-toplevel)"

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: no se encontró el archivo $ENV_FILE en $(pwd)." >&2
  exit 1
fi

## Carga las variables del .env línea por línea.
## Soporta el prefijo 'export', comillas y saltos de línea CRLF.
while IFS= read -r line || [ -n "$line" ]; do
  line="${line%$'\r'}"

  ## Ignorar líneas vacías y comentarios
  case "$line" in
    ''|'#'*) continue ;;
  esac

  line="${line#export }"

  ## Debe tener formato key=value
  case "$line" in
    *=*) ;;
    *) continue ;;
  esac

  key="${line%%=*}"
  value="${line#*=}"

  ## Remover comillas envolventes si las hubiera
  if [ "${value#\"}" != "$value" ] && [ "${value%\"}" != "$value" ]; then
    value="${value#\"}"; value="${value%\"}"
  elif [ "${value#\'}" != "$value" ] && [ "${value%\'}" != "$value" ]; then
    value="${value#\'}"; value="${value%\'}"
  fi

  export "$key=$value"
done < "$ENV_FILE"

## Validar que las credenciales existan y no estén vacías
missing=()
for var in DVC_AWS_ACCESS_KEY_ID DVC_AWS_SECRET_ACCESS_KEY; do
  if [ -z "${!var:-}" ]; then
    missing+=("$var")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "Error: faltan variables (o están vacías) en $ENV_FILE: ${missing[*]}" >&2
  exit 1
fi

dvc remote modify storage --local access_key_id "$DVC_AWS_ACCESS_KEY_ID"
dvc remote modify storage --local secret_access_key "$DVC_AWS_SECRET_ACCESS_KEY"

echo "Credenciales del remote de DVC configuradas correctamente."
