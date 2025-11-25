# Pull request sugerido

## Título
Exponer consultas NL-to-SQL con ChatGPT y caché de esquema

## Resumen
- Conecta a PostgreSQL leyendo configuración desde `config/database.toml` o `WAITRAIN_CONFIG` y valida DSN y credenciales del LLM al iniciar.
- Extrae y cachea el esquema en disco y memoria para acelerar consultas posteriores.
- Genera SQL y resúmenes en español usando el modelo configurado de ChatGPT y muestra resultados en la UI web minimalista.

## Pruebas
- `python -m compileall app`
