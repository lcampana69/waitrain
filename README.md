# waitrain

Aplicación web mínima para consultas en lenguaje natural contra bases de datos PostgreSQL.

## Características
- Lee la configuración de conexión desde `config/database.toml` (o la ruta indicada en `WAITRAIN_CONFIG`).
- Extrae y cachea el esquema de la base de datos en `data/schema_cache.json` para reutilizarlo en sesiones posteriores (el archivo se comparte entre ejecuciones y además se memoiza en memoria por proceso).
- Expone una interfaz web simple (`/`) para enviar preguntas en lenguaje natural.
- Genera SQL con ChatGPT a partir de la pregunta y el esquema detectado, ejecuta la consulta y devuelve un renderizado resumido.
- Incorpora un panel de debug en la UI y un endpoint de diagnóstico para detectar problemas de conexión o configuración.

## Requisitos previos
- Python 3.11+
- PostgreSQL accesible desde el host donde se ejecute la app.

## Configuración
1. Copia y ajusta `config/database.toml` con tu DSN de PostgreSQL (campo obligatorio), la configuración del modelo LLM (por defecto `gpt-5.1-mini`) y, si lo deseas, la ruta del caché de esquema o el prompt del sistema. Si prefieres otro fichero, define `WAITRAIN_CONFIG=/ruta/a/mi_config.toml` al arrancar la app. Si la ruta indicada no existe el servidor fallará al iniciar, para evitar usar configuraciones equivocadas.
2. Instala dependencias:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Exporta la clave de API de OpenAI (por defecto `OPENAI_API_KEY`, puedes cambiar el nombre de la variable en la sección `[llm]` del TOML):
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

### Campos principales del TOML
- `[database].dsn`: cadena de conexión completa a PostgreSQL (obligatoria).
- `[database].schema_cache_path`: ruta al fichero de caché del esquema (opcional, por defecto `data/schema_cache.json`).
- `[database].system_prompt`: prompt base para dirigir al LLM al generar SQL (opcional).
- `[llm].model`: nombre exacto del modelo de chat a usar (por defecto `gpt-5.1-mini`).
- `[llm].api_key_env`: variable de entorno de donde leer la API key (por defecto `OPENAI_API_KEY`).

## Ejecución
1. Arranca el servidor:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Abre [http://localhost:8000](http://localhost:8000) y lanza preguntas en lenguaje natural.

### Problemas frecuentes
- Error `ModuleNotFoundError: No module named 'openai'`: instala las dependencias con `pip install -r requirements.txt` antes de iniciar.
- Al preguntar aparece un error de configuración JSON: revisa la "Ventana de debug" en la UI, que muestra la respuesta exacta del servidor.
  - Usa el botón **Diagnóstico** para validar que el fichero TOML exista, que la conexión a la base de datos funcione y que el caché de esquema se genere.
  - Corrige la ruta del TOML (`WAITRAIN_CONFIG`), el DSN o las credenciales según el mensaje devuelto.

### Flujo de trabajo
1. La API carga configuración y valida DSN y credenciales de LLM al iniciar.
2. Si no existe caché de esquema, introspecciona la base de datos y guarda el resultado en disco y memoria.
3. El endpoint `/ask` recibe la pregunta, genera SQL con el esquema cacheado y el modelo configurado, ejecuta la consulta y devuelve los resultados junto con un resumen en español.
4. La UI muestra el SQL generado, el resumen y los datos tabulados.

## Contribuir
- Crea ramas pequeñas con cambios acotados.
- Acompaña tus PRs de una descripción clara y pruebas manuales si aplica.