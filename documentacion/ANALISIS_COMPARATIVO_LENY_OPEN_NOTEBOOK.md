# Comparación técnica LENY / Open Notebook

Fecha de inspección: 03/11/2026. Estado: **diseño para revisión; no implementado**.

## 1. Conclusión ejecutiva

LENY no necesita sustituir su infraestructura ni reproducir Open Notebook. Ya implementa búsqueda híbrida con RRF, búsqueda autorizada por título, selección conjunta, empaquetado adaptable, síntesis estructurada, pasajes de soporte y revalidación. La comparación no justifica presentar esas funciones como novedades.

Open Notebook ofrece tres experiencias diferentes: Chat usa contexto elegido; Source Chat concentra contexto de una fuente; Ask planifica búsquedas, redacta respuestas intermedias y las sintetiza. Sus prácticas aprovechables son delimitar explícitamente la fuente/sección consultada, conservar estructura durante la fragmentación y hacer visible el alcance del contexto. Su validador no resuelve el problema semántico de LENY: valida principalmente estructura de la estrategia, salidas vacías y sintaxis de referencias; no demuestra respaldo de cada afirmación. [O3, O5–O10]

La dificultad actual de LENY está distribuida entre estructura/cobertura, selección, generación y validación. Flexibilizar coincidencias literales evita algunos falsos rechazos, pero no convierte la presencia de una cifra en prueba de su relación con una entidad o condición. Tampoco arregla una responsabilidad que no figure inequívocamente en el original. Los resultados históricos más recientes incluyen **527 pruebas seleccionadas** y tres turnos backend reales repetidos, pero la respuesta sobre encargada siguió siendo general y sin fuentes. No existe aceptación funcional global acreditada por esos resultados. [L3, L7–L9]

Se proponen cinco adaptaciones incrementales: contexto de sección verificable; consulta explícita de fuente con cobertura acotada; síntesis con soporte localizado y causas de rechazo diferenciadas; continuidad basada en progreso comprobable; presentación del alcance y diagnóstico por etapa. Primero se compararán variantes aisladas, con el mismo modelo y evidencia. No se recomienda activar planificación multibúsqueda, resúmenes derivados ni índices nuevos sin un fallo medido que los justifique.

## 2. Versiones, alcance y límites

### 2.1. Identificación de las fuentes

| Fuente | Identificación inspeccionada | Alcance y límite |
|---|---|---|
| Open Notebook, repositorio lfnovo/open-notebook | Etiqueta v1.15.0 → **315d5255af2a5132aada41c94d5c3c5dc8e837aa** | Referencia fijada por API GitHub; archivos leídos directamente por HTTPS desde el original, sin clonarlo, guardarlo ni ejecutar sus scripts. Los enlaces O fijan ese SHA. |
| Referencia anterior mencionada en la solicitud | a0f6f3081ae06328f0a451b3a3ef2959ca25721d | Sustituida por instrucción posterior del propietario. No se ha realizado un diff completo entre ambos commits; no se mezclan sus implementaciones. Las cifras y funciones de este informe corresponden a v1.15.0. |
| BELLAARTE / LENY, repositorio local bellaarte-program | HEAD **5a1d15a04c2f97483769c86e82dbba056adce6b8**, más cambios locales preexistentes | HEAD por sí solo no identifica el código actual. El apéndice registra huellas de archivos críticos del árbol de trabajo. No se revirtieron ni completaron esos cambios. |
| Requisitos y continuidad LENY | SPEC-01, 02, 03 y 04; MODULO_LENY, REPORTE_IMPLEMENTACION_LENY y LENY_RAG_V11_IMPLEMENTACION | Se contrastaron requisitos, código y últimas actualizaciones. No se localizó un archivo independiente denominado continuidad/handoff; los informes y referencias de SPEC-04 cumplen esa función documental. |

En Open Notebook se revisaron los manifiestos, licencia, VISION, documentación de arquitectura/procesamiento/pruebas/contexto/citas, los cinco grafos solicitados, utilidades, dominio/repositorio, migraciones 1–25, comandos, routers, autenticación, plantillas, componentes y pruebas pertinentes. Se revisó la integración con content-core y su versión fijada; **no su implementación externa completa ni los binarios de sus motores**.

En LENY se inspeccionaron los servicios solicitados y sus dependencias inmediatas de ingesta, publicación, almacenamiento, seguimiento, coordinación e interfaz. Se leyeron pruebas relevantes sin ejecutarlas. Los contenidos privados de manuales y las respuestas históricas privadas no se copiaron a este informe ni se enviaron a GitHub u otro servicio.

**Operaciones de esta revisión:** lecturas de código/documentación/Git, lectura de configuración mediante Settings sin importar aplicación/router y consultas HTTPS al repositorio público. No se abrieron conexiones de base de datos, no se ejecutaron inferencias, pruebas con persistencia, migraciones, instalaciones, arranques ni cambios de configuración. El único archivo creado por esta tarea es este informe.

Los hallazgos se distinguen así:

- **Código:** comportamiento ejecutable demostrado en los archivos citados, sin atribuirle resultados empíricos nuevos.
- **Documentación:** intención o resultados anteriores declarados; no se convierten en una ejecución de esta revisión.
- **Hipótesis/experimento:** beneficio que debe medirse antes de adoptar una adaptación.

### 2.2. Configuración de LENY comprobada

Lectura independiente del cargador Settings desde backend, con su .env y las variables heredadas de esa terminal; solo se imprimieron campos técnicos permitidos. No se consultó la memoria del proceso Uvicorn activo: un proceso que conserve configuración anterior en caché debe comprobarse en una futura ejecución autorizada. No se exponen conexiones ni credenciales. [L2]

| Parámetro | Valor cargado |
|---|---|
| Generación | qwen3.5:4b-q4_K_M; contexto 4096; salida máxima 768; temperatura 0; keep_alive 0 |
| Variante | controlled-synthesis-v1; perfil rag4_v1; chat documental habilitado |
| Recuperación | hybrid; hasta 20 candidatos; top_k 5 |
| Vecinos | Código ±1 existente; **leny_rag_neighbor_chunks=false** en esta lectura |
| Evidencia | adaptive; sondeo de tokens habilitado |
| Embeddings | qwen3-embedding:0.6b; dimensión 1024; 4 hilos; lotes 2; adaptador exige CPU |
| Fragmentación | Objetivo 1600 caracteres; máximo 2000 caracteres / 3072 bytes; overlap configurado 240 caracteres |
| Memoria y tiempo | Margen de RAM 2 GiB antes / 1 GiB residente; plazo total 120 s |
| Ciclo de vida | leny_runtime_autostart=true; gestión de procesos propios en lifespan |

El valor predeterminado en código continúa siendo document-excerpts-v2. **Ese predeterminado no es el modo cargado actualmente.** Vecinos implementados tampoco significa vecinos activados. Las referencias históricas al worker exclusivamente manual quedan superadas por el runtime actual, que inicia/reutiliza servicios y distingue procesos propios de externos. [L2, L14]

El stack local inspeccionado sigue siendo FastAPI/Python, SQLAlchemy/Alembic, PostgreSQL/pgvector y React/Ant Design con NDJSON. Python 3.10.6, PostgreSQL 17.9 y el equipo Ryzen 5 8645HS / RTX 4050 6 GB / 16 GB RAM son referencias de entorno documentadas/aportadas, no mediciones nuevas de esta revisión. Los manifiestos y código confirman la arquitectura; no se revalidaron aquí todas las versiones instaladas. [L1, L15]

Open Notebook declara Python >=3.11,<3.13, FastAPI, LangChain/LangGraph, Esperanto, SurrealDB y content-core; su frontend declara Next ^16.3.8 y React ^19.3.0. No es código trasladable como bloque a Python 3.10.6 ni requiere cambiar React/Ant Design para adaptar una idea. Son versiones de manifiesto, no un runtime ejecutado por esta revisión. Su licencia es MIT; cualquier futura copia de código deberá conservar avisos y licencia, además de revisar las licencias de las dependencias efectivamente incorporadas. Este informe propone diseño, sin copiar implementación. [O1]

## 3. Flujos reconstruidos

### 3.1. Open Notebook

~~~mermaid
flowchart TD
    A[Archivo, URL o texto] --> B[Validación de entrada y trabajo process_source]
    B --> C[content-core: extracción según motor]
    C --> D[Source: texto completo, título y asset]
    D --> E[embed_source en cola]
    E --> F[Splitter según formato y tokens]
    F --> G[Vector por fragmento en SurrealDB]
    D --> H[Transformaciones opcionales]
    H --> I[Insights derivados y embeddings]
    D --> J[Chat: contexto elegido]
    I --> J
    D --> K[Source Chat: una fuente]
    G --> L[Ask: estrategia y búsquedas vectoriales]
    I --> L
    L --> M[Respuestas parciales y síntesis]
    J --> N[Referencias por ID y apertura de recurso]
    K --> N
    M --> N
~~~

El guardado de la fuente y la finalización de embeddings son momentos distintos. El grafo puede encolar vectorización y transformaciones; éxito de extracción no demuestra índice completo. Texto completo, fragmentos y derivados pueden consultarse por rutas diferentes. [O2, O4]

Ejemplo empresarial: seleccionar un manual para Source Chat proporciona su texto/insights como contexto; preguntar mediante Ask genera términos de búsqueda y combina respuestas intermedias. Ningún filtro de notebook de esos recorridos equivale por sí mismo a permiso ADMIN, CAJA o MODISTA.

### 3.2. LENY actual

~~~mermaid
flowchart TD
    A[ADMIN carga original privado e inmutable] --> B[Versión y ACL]
    B --> C[Trabajo durable, extracción local y cobertura]
    C --> D[Fragmentos trazables y embeddings CPU]
    D --> E[Índice staging validado]
    E --> F[Publicación: versión más índice]
    U[Pregunta y contexto útil del propietario] --> S[JWT/Casbin, seguridad, cuota y capacidad]
    S --> R[Interpretación y título o asunto]
    F --> Q[SQL con publicación vigente y ACL]
    R --> Q
    Q --> V[RRF: vector y texto, máximo 20]
    V --> W[Selección conjunta y controles de ámbito]
    W --> X[Paquete íntegro y presupuesto]
    X --> Y[Qwen: síntesis estructurada en memoria]
    Y --> Z[Validación mecánica y guardia de salida]
    Z --> P[Revalidación, fuentes citadas y NDJSON]
    W --> G[Orientación general permitida y advertida si falta evidencia]
    S --> N[Rechazo o capacidad no disponible]
~~~

La generación no recibe una herramienta para SQL comercial ni permiso para mutar el ERP. El SQL de recuperación lo construye el backend, sobre documentos autorizados. El registro de capacidades ya separa documentos, orientación y redacción de transactional_sql, BI, ML y AutoML deshabilitados. [L4–L9, L13]

Ejemplo: «cómo quedar la fecha de la PRIEMRA PRUEBA» debe interpretarse como procedimiento para acordar una prueba de vestido; no como autorización para leer o reservar una fecha concreta en agenda. Si un manual solo explica cómo coordinarla, la respuesta debe limitarse a ese procedimiento.

## 4. Ingesta, estructura, fragmentación e índices

### 4.1. Extracción y estructura que realmente llega a la búsqueda

**Open Notebook.** content_process delega a content_core.extract_content; configura motores y opciones de OCR/visión/fórmulas/STT según el tipo. La documentación describe motor simple y Docling opcional, con diferencias de tablas, columnas, orden de lectura y OCR. Eso no demuestra que todo PDF de una instalación se procese con Docling ni que exista OCR local configurado. La versión declarada es content-core >=2.2,<3 y uv.lock fija 2.2.0. [O1, O2]

save_source guarda extraction.content como full_text, asset y título. No conserva como campos de fragmento páginas, cajas, offsets ni relaciones explícitas cargo→funciones. Puede llegar estructura expresada como Markdown, pero su calidad depende del extractor delegado. Errores de extracción se traducen a errores controlados y texto vacío se rechaza. Si delete_source está habilitado, puede borrarse el archivo tras extraer y antes de completar vectorización: no adoptar ese ciclo para originales empresariales. [O2]

**LENY.** El extractor propio usa pypdf para texto PDF; pypdfium2/pyvips para rasterización y Tesseract local cuando una página necesita OCR. DOCX se recorre por párrafo y fila de tabla; conserva localizador de bloque/párrafo/tabla/fila y estilo cuando existe. Repite la fila marcada como encabezado en filas posteriores si cabe. Imágenes incrustadas DOCX generan advertencia, no OCR implícito. JPG/PNG usan OCR. Hay límites de tiempo, páginas, memoria, píxeles y temporales; cobertura y advertencias acompañan el índice. [L5]

Limitaciones: una página PDF plana no garantiza tablas ni orden lógico; numeraciones de lista DOCX pueden depender de información de formato que no se materializa como texto; un estilo de encabezado no se propaga actualmente como ruta de sección a todos sus párrafos. No hay un parser semántico general de cargos, dependencias o procedimientos. Esto puede explicar listas recuperadas sin el sujeto que les da significado, pero requiere comprobar los localizadores y el original autorizado de cada caso. [L5, L6]

### 4.2. Fragmentación

| Aspecto | Open Notebook v1.15.0 | LENY actual |
|---|---|---|
| Unidad y tamaño | Por defecto 400 tokens; mínimo configurado 5 tokens; overlap 15% = 60 en el valor predeterminado | Cada unidad extraída se fragmenta independientemente; objetivo 1600 caracteres, máximos 2000 caracteres/3072 bytes |
| Detección | Extensión y heurística sobre los primeros 5000 caracteres; confianza alta puede reemplazar clasificación de texto plano | source_type explícito PDF_TEXT/PDF_OCR/DOCX_PARAGRAPH/DOCX_TABLE/IMAGE_OCR |
| Separadores | HTML h1–h3; Markdown #–###; división secundaria recursiva; texto por párrafo/línea/frase/coma/espacio/carácter | Prefiere párrafo/línea/frase/espacio dentro de la unidad, con límite estricto de bytes |
| Encabezados | Markdown usa strip_headers=False; la salida reduce Document a page_content y descarta metadata | Conserva locator y style recibidos; no hereda automáticamente heading_path |
| Overlap | Tokens según contador genérico | Hasta 240 caracteres y como máximo un cuarto del fragmento; alinea a palabra |
| Fragmentos pequeños | Filtro cuando hay varios y sobreviviría al menos uno; texto corto tiene retorno anticipado | Se conserva unidad corta no vacía; no se fusiona con su encabezado por defecto |
| Procedencia | En embedding: source/order/content/vector | Fragmento con ordinal, tipo, hash y offsets NFC en su unidad |

Evidencia: [O3, O4, L5, L6].

Los 400 tokens de Open Notebook buscan margen frente a embedders de 512 y diferencias de tokenización según su documentación; **no son una recomendación automática para Qwen3-Embedding**. El conteo usa o200k_base o aproximación por palabras, no el tokenizer nativo de Qwen. Los encabezados ayudan a dividir, pero descartar metadata y volver a dividir una sección larga no garantiza que cada subfragmento conserve el encabezado necesario. Open Notebook también puede separar una condición de su paso. [O3]

Para LENY conviene medir primero: cuántas listas pierden cargo/encabezado, cuántos pasos y condiciones se separan y si los fragmentos gold caben junto con su contexto. Comparar únicamente la longitud no identifica calidad estructural. No se propone cambiar globalmente tamaño/overlap ni recontextualizar todo el corpus.

### 4.3. Embeddings, indexación y trabajos

**Open Notebook.** Cada chunk de fuente tiene vector propio; nota e insight guardan un vector de registro. Para notas/insights largos se fragmenta y aplica normalización por vector → media sin ponderación por longitud → normalización final. Ese pooling pierde localización fina: sirve para localizar un derivado completo, no para demostrar cada afirmación del original. El proveedor/modelo de embeddings es configurable; no existe una dimensión universal ni la misma identidad de modelo garantizada por el esquema de source_embedding. [O4]

Los lotes de generate_embeddings son secuenciales, por defecto 50 configurables, con tres intentos y espera fija; la capa de comandos añade sus políticas. process_source admite hasta 15 intentos con jitter; embed_source hasta 5 según clase de error. Algunos ValueError/NotFoundError se convierten en success=false y no en excepción de trabajo. Rebuild cuenta envíos, no trabajos concluidos. El transporte y worker de surreal-commands son una dependencia: no atribuir su implementación a Open Notebook. [O4, O12]

embed_source borra embeddings anteriores antes de reconstruir. Si falla INSERT, intenta limpiar los parciales; no hay cambio atómico de un índice publicado equivalente al de LENY. La ruta de alta examinada crea Source nuevo sin deduplicación por hash/URL; algunos fallos de limpieza se registran y continúan. Son límites observados estáticamente, no incidentes reproducidos aquí. [O12]

**LENY.** Modelo/digest, dimensión, pipeline y políticas se fijan en indexación; embeddings son 1024 en CPU, lotes 2 en la configuración leída. El adaptador valida identidad, vectores finitos/no nulos y ejecución CPU; no trunca silenciosamente. El worker guarda checkpoints, omite fragmentos ya vectorizados, usa token/lease/heartbeat y coordina inferencias con el chat. La publicación apunta a versión e índice validados; un staging incompleto no reemplaza la publicación vigente. Idempotencia de trabajo y hash de fragmento no significan eliminar textos iguales de localizaciones distintas. [L5, L12–L14]

El borrado/reconstrucción de derivados sigue controles de versión/publicación y operaciones administrativas; debe conservarse. No adoptar el borrado previo de Open Notebook ni cambiar a su cola.

### 4.4. Índices físicos frente a búsqueda

Open Notebook crea seis índices textuales BM25 en migración 1 y añade índices ordinarios por FK en 10. El analizador original combina separación de tokens, minúsculas y stemming inglés; ese detalle no es una mejora automática para español. Tras aplicar migraciones en orden, la función vectorial vigente es la de 24 y la textual es reemplazada por 25. No se encontraron declaraciones HNSW/MTREE en las migraciones 1–25 inspeccionadas. La búsqueda vectorial final calcula similitud coseno explícita con chequeos de dimensión. **Vectorial no implica ANN.** [O11]

LENY usa distancia coseno pgvector y búsqueda textual PostgreSQL en español. La migración 0020 no crea HNSW/IVFFlat; el SQL actual calcula ranking exacto sobre elegibles. Tener embeddings, índice lógico versionado e índice físico de aceleración son hechos distintos. Sin EXPLAIN/volumen autorizados no se atribuye el fallo de selección a ausencia de ANN ni se propone un índice nuevo. [L6, L12]

## 5. Recuperación, selección y contexto

### 5.1. Qué buscador usa cada ruta

| Ruta Open Notebook | Recuperación real |
|---|---|
| API de búsqueda textual | text_search → función BM25 final de migración 25 |
| API de búsqueda vectorial | vector_search → embedding de consulta y función final de migración 24 |
| Chat | Construye contexto según selección; el grafo no ejecuta RAG vectorial automáticamente |
| Source Chat | Reconstruye contexto de una fuente específica y sus insights |
| Ask | Por cada término planificado llama vector_search(term,10,True,True,notebook_ids=...) |

Las funciones textual y vectorial son independientes. El fallback textual→vectorial solo aparece para un error concreto de position overflow; no es fusión híbrida ni RRF. Hay búsqueda BM25 de títulos, pero Ask no convierte automáticamente la mención de un título en selección autorizada de esa fuente. [O5, O6, O11]

En vector_search el umbral predeterminado es 0.2. La función SQL limita ramas, agrupa por id/parent/title, usa máxima similitud y reúne contenidos en matches, antes del límite final. El top 10 de Ask cuenta **resultados agrupados**, que pueden contener varios matches; no significa diez fragmentos de tamaño fijo ni diez citas de pasaje. Insights conservan su identidad con parent_id hacia la fuente; la migración 25 corrige esa relación en búsqueda textual. [O6, O11]

El filtro notebook valida formato/existencia y pertenencia. Lista vacía puede significar toda la base. No recibe identidad/rol/ACL empresarial. [O11, O13]

**LENY.** ELIGIBLE comprueba cuenta/usuario/rol habilitados, restricción de cambio de clave, documento activo no eliminado, versión e índice publicados, compatibilidad y conteos, y ACL antes del ranking. La búsqueda explícita de título opera dentro de esa población: coincidencia normalizada exacta o parcial acotada; inexistente y restringido no se distinguen al usuario; varias coincidencias autorizadas producen aclaración. No equivale a un resolvedor general de cualquier título escrito informalmente. [L6]

RRF fusiona hasta 10 resultados semánticos y 10 léxicos con constante 60, deduplica por fragmento y conserva hasta 20. No compara directamente escalas de BM25/coseno; la rama textual usa ts_rank_cd, no BM25. La expansión ±1 existe dentro del mismo índice y respeta fronteras fiables en V1.1, pero está desactivada en la configuración leída. No hay MMR ni umbral de similitud calibrado actualmente. [L6]

### 5.2. Selección, completitud y presupuesto

LENY preselecciona y solicita un plan conjunto de aspect/scope/relation/sources. En V1.1 conserva el pool contextual de hasta 20; el plan puede seleccionar hasta 5 **fragmentos**, no necesariamente cinco documentos. Se verifican forma, IDs, ámbito y coherencia mecánica. El veto de responsabilidades exige atribución en texto o encabezado del localizador; el título del archivo no basta. También hay controles acotados de inventario/materiales y cantidades solicitadas. Son barreras parciales, capaces de provocar falsos negativos cuando falta el encabezado, no pruebas de entailment. [L7]

El presupuesto de entrada reserva 768 de salida y 256 de margen dentro de 4096: **3072 tokens presupuestados para la entrada**. El cálculo inicial por bytes UTF-8 es conservador, no un conteo equivalente de tokens. Cuando corresponde, los sondeos obtienen contadores reales de Ollama, repiten la medición y fallan si es incierta; consumen inferencia aunque solo generen un token. La síntesis mide su prompt y esquema reales, no reutiliza una medida de otro prompt. [L8–L10]

Con instrucciones, IDs, contexto de seguimiento y esquema, no todo ese presupuesto queda disponible para documento. No se debe llenar con páginas completas ni truncar la condición que cambia un paso. Una consulta explícita de todos los pasos puede marcarse parcial si no se recuperan todos los fragmentos, pero contar fragmentos de un documento tampoco identifica por sí mismo los límites de un procedimiento. Esa es una deuda de estructura/cobertura, no necesariamente de embeddings. [L7, L8]

Open Notebook usa o200k_base/fallback aproximado. build_notebook_context no aplica un presupuesto total; Source Chat limita a 50.000 tokens **solo el contexto de fuente**, reservando en exceso de texto un 20% para insights y un prefijo del original con aviso. Historial/sistema/salida no quedan incluidos en ese límite. La selección automática de modelo large_context por más de 105.000 tokens tampoco demuestra ajuste a la ventana real. No trasladar esos límites a LENY. [O7]

### 5.3. Coste de Chat, Source Chat y Ask

| Recorrido | Llamadas y límites observados |
|---|---|
| Chat | Una generación por turno; historial almacenado completo más contexto seleccionado; solicita hasta 8192 de salida |
| Source Chat | Una generación; historial completo y contexto de fuente acotado a 50.000; solicita hasta 8192 |
| Ask | s términos despachados implican s embeddings/búsquedas; r búsquedas con resultados implican r llamadas de respuesta, aunque alguna salida se descarte por vacía. Con estrategia y síntesis completadas: r+2 generaciones, r<=s |
| Transformación | Generación para derivado; su vectorización es trabajo adicional según recorrido |
| LENY documental | 0–2 llamadas de clasificación contextual si hacen falta, una selección conjunta, una síntesis; embedding de consulta y sondeos variables bajo el mismo coordinador |

En Ask «hasta cinco búsquedas» está en la descripción Pydantic; List[Search] no impone max_length, ni trigger_queries recorta la lista. Los términos vacíos se eliminan. Cada búsqueda se despacha por Send y no hay max_concurrency explícito en esa ruta. No se afirma que LangGraph/proveedor carezcan de cualquier límite interno; sí que este código no fija el límite empresarial necesario para nuestra GPU. Con cinco búsquedas con resultados serían siete generaciones, cada una solicitando hasta 8192: un techo solicitado agregado de 57.344 tokens de salida, no salida real medida ni presupuesto global de 8192. La lista no tiene un máximo efectivo de cinco impuesto por ese esquema. [O6]

LENY serializa la inferencia y mantiene plazo/cuota/RAM. Las mediciones no deben registrar solo los 768 de respuesta: hay que sumar clasificadores, selección y sondeos; estos pueden añadir cargas repetidas con keep_alive=0. El número exacto es dependiente de rama. No se propone imitar el fan-out de Ask. [L4, L8, L10, L13]

## 6. Síntesis, validador, citas y continuidad

### 6.1. Qué garantiza y qué no garantiza cada validador

| Capa | Open Notebook v1.15.0 | LENY actual |
|---|---|---|
| Planificación/selección estructurada | PydanticOutputParser valida Strategy; elimina términos blancos; sin máximo efectivo de cinco | Plan JSON de aspecto/ámbito/relación, máximo de IDs y verificación backend |
| Redacción | Chat, Source Chat y Ask generan texto; prompts piden fuentes y no inventar IDs | Síntesis JSON, máximo 4 bloques documented/general/example, soportes P por fuente y limitación explícita |
| Salida incompleta | Chats/Ask rechazan vacío después de retirar pensamiento; no comprueban toda terminación por longitud | Síntesis rechaza finish_reason=length antes de emitir; validación completa en memoria |
| Excepción útil | Transformación sí comprueba length/max_tokens y vacío antes de guardar insight | Se conserva rechazo de salida documental incompleta; no fallback extractivo silencioso |
| Referencias | Parser frontend reconoce tipo/ID, normaliza alias, deduplica y abre recurso | Backend liga fuente/pasaje, comprueba referencias y persiste solo fuentes citadas; apertura revalida |
| Afirmaciones | No se encontró verificador posterior de soporte semántico en los grafos/rutas inspeccionados | Cifras/unidades, actores y condiciones acotadas; identidad válida no demuestra entailment |
| Seguridad de negocio | Contraseña compartida opcional y ámbito notebook | JWT/Casbin, ACL SQL, propietario, cuota, revocación y herramientas no habilitadas |

Evidencia: [O5, O6, O8–O10, O13, L4, L7–L10, L13].

**Open Notebook no proporciona un validador semántico más fuerte que podamos copiar.** Sus prompts solicitan IDs exactos; el frontend comprueba sintaxis/tipo/longitud y puede mostrar recurso inexistente. Abrir una fuente/nota/insight completo no demuestra qué pasaje respalda la afirmación. La documentación de citas recomienda verificación humana; sus promesas generales de citas en toda respuesta y resaltado exacto son más fuertes que lo acreditado por los componentes examinados. No confundir esa intención con control ejecutable. [O9, O10]

En Ask, provide_answer devuelve answers vacío cuando una búsqueda no encuentra resultados y descarta texto intermedio vacío después de generar. write_final_answer no comprueba que exista alguna respuesta intermedia antes de invocar la síntesis: renderiza pregunta, estrategia y answers. El prompt pide evitar especulación y reconocer incertidumbre, pero no hay una abstención determinista previa para ese caso. Es una diferencia de control confirmada en código, no una alucinación reproducida en esta revisión. Además, la última síntesis trabaja con respuestas intermedias, por lo que puede perder condiciones aunque los IDs se conserven. [O6,O9]

En LENY, source_passages crea unidades de oración y conserva pasos/listas y algunas condiciones dependientes. El esquema une source con IDs de sus pasajes. El validador acepta paráfrasis, evita ciertas prohibiciones/negaciones incompatibles y comprueba actores explícitos. La flexibilización ya retirada de marcadores literales no debe reintroducirse. [L9]

**Límite actual relevante:** números/unidades pueden comprobarse sobre todos los fragmentos seleccionados del mismo indexation_id y añadir fuentes hermanas al pie. Esto evita un falso rechazo entre páginas del mismo manual, pero permite mecánicamente que una cifra presente en otro asunto pase el control de presencia. Tampoco preserva automáticamente entidad, material, condición, modalidad o excepción. Los bloques pueden contener varias afirmaciones con un único conjunto de soportes; faltan pruebas independientes de esa asociación. Las listas de números no expresan semántica; numeraciones de pasos también requieren tratamiento distinto de cantidades empresariales. [L9]

La ausencia de una cita válida es un error distinto de una paráfrasis semánticamente fiel rechazada, y distinto de evidencia que no responde. El mensaje común «no pude completar una síntesis fiable» se usa para varios ValueError/TypeError/KeyError, incluido contexto, referencias y contenido. Es correcto no publicar una síntesis no validada, pero ese mensaje único oculta la causa al diagnóstico. No prueba por sí mismo fallo del modelo ni falta de documentación. [L8, L9]

### 6.2. Normas, ejemplos y orientación

Publicación habilita uso para un rol; no convierte una plantilla en norma aprobada. El prompt actual lo indica y diferencia documented/general/example. La clasificación jurídica/organizacional de un manual necesita metadatos o texto inequívoco, no una inferencia desde nombre o publicación. [L9]

La orientación general sin citas ya está permitida en ramas concretas y lleva aviso; si no queda evidencia documental, existe un recorrido general advertido. No proponer esa capacidad como nueva. La mejora pendiente es decidirla de forma consistente y evitar que una pregunta sobre una responsabilidad interna se presente como contestada documentalmente porque recibió estado answered con consejos generales. La interfaz y la evaluación deben distinguir esas categorías. [L8, L9]

Para «quiero un ejemplo de cómo iniciar un manual» una plantilla adaptable puede ser útil sin fuente. Para «según el documento EJEMPLO DE COMO INICIAR EL MANUAL» se debe intentar la búsqueda autorizada y separar cualquier complemento general de lo explicado por ese ejemplo. No inventar aprobación ni cifras internas para completar la plantilla.

### 6.3. Historial y «¿Y después?»

Open Notebook Chat y Source Chat conservan mensajes en SQLite mediante checkpointer; metadatos y relaciones de sesión están en SurrealDB. La frase documental que mezcla ambos almacenamientos no se toma literalmente. Ask se compila sin checkpointer y su estado no incorpora historial: no es una solución directa al seguimiento conversacional. [O5–O7]

LENY usa propietario y versión de política; topic_history conserva un ancla reciente del usuario. Para seguimiento recupera de nuevo con ACL/publicación y puede acotar a documentos anteriores. followup_progress devuelve hasta 1200 caracteres de respuesta anterior solo si sus fuentes siguen elegibles; se trata como progreso, nunca como nueva evidencia. La síntesis recibe instrucciones de continuar sin repetir. El modo extractivo tiene un helper separado para siguiente punto numerado. Todo esto **ya existe**. [L8, L11]

Falta una representación explícita y verificable de qué parte del procedimiento se explicó y cuál sigue. Un ancla de 400 caracteres y un recorte final de respuesta no garantizan continuidad, especialmente si hubo un resumen global o varios procedimientos. Añadir historial completo indiscriminadamente gastaría contexto y podría resucitar hechos revocados. La adaptación propuesta es reconstruir progreso acotado desde referencias vigentes y sección/ordinal comprobados, con aclaración solo ante varias secuencias o final documental real; nunca inferir un paso interno ausente.

## 7. Interfaz, trabajos y seguridad a conservar

Open Notebook permite elegir contexto excluido/insights/texto completo, muestra conteo de ese contexto y abre referencias por ID. El indicador no reserva historial/sistema/salida ni bloquea exceso del modelo. Source Chat SSE emite resultado después de invoke completo; Ask emite actualizaciones de nodos. No atribuir streaming de tokens solo por usar SSE. Su UI consulta estados de procesamiento y reintenta sondeos de trabajos. [O5, O7, O10, O12]

LENY ya muestra espera/verificación, errores, reintentos de cuota, fuente/versión/localizador, advertencias y panel administrativo con progreso, cancelación y reintento. Markdown elimina HTML e imágenes y neutraliza enlaces activos; abrir/descargar fuente vuelve a autorizar y retira acceso ante 403/404. No requiere cambiar de framework. Falta exponer al usuario un alcance breve como «respuesta parcial de esta sección» y facilitar «resumir esta fuente» con identidad backend autorizada, sin mostrar métricas de implementación en el flujo habitual. [L15]

No copiar ciegamente el manejo de trabajos: en la versión examinada list_command_jobs devuelve lista vacía y cancel_command_job solo registra y devuelve true; el DELETE expone ese resultado sin cancelación efectiva. La guardia de retry_source_processing que pretende bloquear running/queued captura su propia HTTPException mediante except Exception. Son hallazgos estáticos de esas rutas, no una afirmación de que todos los mecanismos externos de surreal-commands fallen. [O12]

Conservar especialmente en LENY:

- JWT/Casbin e identidad individual con cuenta/usuario/rol habilitados.
- ACL dentro del SQL antes de ranking, incluso en títulos, vecinos, secciones y cualquier futura ayuda derivada.
- Versiones inmutables, staging validado y publicación fijada a versión+índice.
- Propietario de conversación/fuente; revalidación al recuperar, generar, emitir, consultar historial y abrir fuentes.
- Tratamiento de consulta/documento/salida como datos no confiables; no herramientas autónomas ni cambios comerciales.
- Lease compartido, cuarentena de inferencia incierta, cuota y márgenes de RAM.
- Diagnóstico sin texto privado y revisión humana de la fidelidad.

Open Notebook se declara single-user-first. PasswordAuthMiddleware puede deshabilitarse si no hay contraseña configurada; cuando existe utiliza Bearer con contraseña compartida. La pertenencia a notebook y vínculo sesión/fuente son controles útiles de integridad de contexto, pero no reemplazan estos controles empresariales. [O13, L6, L8, L11–L15]

## 8. Matriz de diferencias y adaptación mínima

Estados relativos a LENY: **ya existe**, **existe parcialmente**, **ausencia confirmada en el alcance inspeccionado**, **por confirmar**, **no aplicable**. Una ausencia acotada no equivale a auditoría de todo el repositorio.

| Componente | Open Notebook: mecanismo/evidencia | LENY: mecanismo/evidencia y estado | Diferencia confirmada | Beneficio empresarial | Recursos | Riesgo | Adaptación mínima | Prioridad |
|---|---|---|---|---|---|---|---|---|
| Extracción | content-core y motores configurables [O2] | Extractor/OCR local, cobertura/localizadores; ya existe [L5] | Dependencia generalista frente a pipeline local trazable | Diagnosticar pérdida de estructura | OCR ya acotado | Motor nuevo cambia resultados/consumo | Auditar original→unidades; conservar motores | P1, sin reemplazo |
| Contexto de sección | Splitters por h1–h3; metadata descartada [O3] | Estilo/localizador sin herencia general; existe parcialmente [L5,L6] | No hay superioridad completa de ON; sí separación estructural explícita | No mezclar cargos ni perder requisitos | Más bytes por evidencia | Encabezado falso/atribuido | Paquete de sección verificable con procedencia | P1 |
| Fuente explícita | Source Chat reconstruye una fuente; 50k de contexto [O5,O7] | Resolución por título ya existe; consulta/resumen por cobertura específico parcial [L6–L8] | Modalidad dedicada frente a recuperar top fragmentos de un título | Resumir encargada/manual extenso de forma honesta | Lectura SQL adicional acotada | Prometer resumen completo | Selector fuente/sección autorizado, sin 50k | P1 |
| Embeddings | Configurables, chunks y pooling de derivados [O4] | Modelo/digest/1024/CPU fijados; ya existe [L5,L12] | Pooling no aporta precisión de soporte | Preservar compatibilidad | Ningún coste nuevo recomendado | Mezclar modelos/versiones | Conservar configuración; no reembedding global | Conservar |
| Texto/vector | BM25 y coseno separados [O11] | RRF híbrido en español activo; ya existe [L6] | LENY ya fusiona rankings | Mejor cobertura léxica/semántica | 2 rankings SQL acotados | Confundir relevancia con respaldo | Medir selección antes de cambiar ranking | Conservar |
| Umbral/MMR | Umbral coseno 0.2; MMR no observado en estas rutas [O11] | Sin umbral calibrado ni MMR; ausencia confirmada aquí [L6] | ON descarta por score, no demuestra umbral transferible | Eventual reducción de ruido | MMR CPU pequeño; evaluación mayor | Perder fragmentos necesarios | Experimento solo si error de ranking medido | Posponer |
| Vecinos | Sin expansión ±1 en recuperador inspeccionado [O11] | Implementados, desactivados; ya existe [L6,L2] | ON no aporta esta técnica | Recuperar condición/paso contiguo | SQL/contexto adicional | Cruzar cargo o sección | Expansión selectiva y fronteras, no activación global | P1 experimental |
| Selección | Ask redacta por resultados agrupados [O6] | Plan único aspecto/ámbito/relación; ya existe [L7,L8] | LENY explicita relación pedida | Evitar tarifas como inventario | Una clasificación acotada | Falsa abstención | Mejorar contexto/diagnóstico antes de añadir jueces | P1 |
| Síntesis | Texto libre y síntesis de respuestas parciales [O6,O8] | JSON con soportes y separación general; ya existe [L9] | LENY vincula más finamente identidad de evidencia | Respuesta útil con límites | 768 salida, 4096 total | Validar forma sin semántica | Afinar contrato y asociación de afirmaciones | P1 |
| Citas/validador | IDs de recurso, instrucciones de prompt [O9,O10] | Pasajes, localizadores y revalidación; semántica parcial [L9,L13] | ON no tiene verificador de afirmaciones equivalente más fuerte | Citas que respaldan lo afirmado | Chequeos CPU; no LLM extra por defecto | Cifra prestada del mismo índice | Soportes explícitos de bloque y pruebas de asociación | P1 |
| Seguimiento | Historial completo Chat/Source Chat; Ask sin historial [O5,O6] | Ancla, progreso y recuperación actual; existe parcialmente [L11] | No falta historial; falta progreso procedimental fiable | «¿Y después?» útil y sin repetición | Contexto acotado | Reutilizar evidencia revocada | Progreso por sección/IDs actuales | P2 |
| Derivados | Transformaciones/insights recuperables [O4,O8] | Sin ese subsistema empresarial autorizado en flujo inspeccionado | Ausencia confirmada aquí | Localizar asuntos de documentos largos | Generación, storage e invalidación | Derivado tratado como norma | Posponer; contrato separado de originales | P3 |
| Planificador | Ask: r+2 generaciones y fan-out sin tope cinco efectivo [O6] | Una recuperación híbrida y selección; ausencia confirmada de Ask equivalente | Mayor descomposición y coste, sin beneficio medido local | Pregunta compuesta si una búsqueda falla | Varias inferencias/búsquedas | Latencia y evidencia degradada entre síntesis | Probar descomposición determinista primero | P3 |
| UI/contexto | Selección, indicador parcial y modales [O7,O10] | Fuentes, espera y panel de trabajos ya existen [L15] | Falta alcance de respuesta y selección de fuente integrada | Entender qué respalda la respuesta | Coste frontend pequeño | Confundir completado con fiable | Etiquetas documentado/parcial/general y acción de fuente | P2 |
| Jobs/cancelación | Cola externa y límites de rutas observados [O12] | Durable, cancelación/leases/checkpoints; ya existe [L12,L14] | LENY tiene controles más apropiados para recursos compartidos | Continuidad de ingesta | Mantener worker existente | Copiar éxito ficticio/cancelación aparente | Conservar y verificar regresión | Conservar |
| ACL/publicación | Password opcional y notebook scope [O13] | ACL SQL, publicación/versiones/propietario; ya existe [L6,L13] | No equivalencia de seguridad | No filtrar documentos internos | SQL/revalidaciones existentes | Exponer existencia o contenido | Conservar todas las barreras | Bloqueante |
| SQL/BI/ML/AutoML | No es solución ERP equivalente en estos flujos | Registry deshabilitado; no aplicable implementarlo ahora [L4] | Futuro contrato empresarial propio | Analítica trazable posteriormente | No coste presente autorizado | Confundir predicción con hecho | Mantener separación de capacidades | Futuro |

## 9. Causas raíz y estado de la evidencia empresarial

| Síntoma reportado | Causa demostrada o límite | Qué no se puede concluir |
|---|---|---|
| Preguntas válidas rechazadas | Clasificación híbrida conservadora y necesidad de contexto; actualmente existen reglas empresariales, normalización acotada y revisión contextual [L4] | No todo rechazo futuro tiene esa misma causa; seguridad legítima no debe relajarse |
| Mención documental sin búsqueda útil | Antes título no participaba; hoy sí se resuelve dentro de ELIGIBLE, para patrones explícitos [L3,L6] | No es ausencia actual general de búsqueda por título; una referencia informal puede requerir desambiguación |
| Fragmentos temáticos irrelevantes | Ranking recupera proximidad; selección y cobertura no equivalen a cercanía; listas sin sujeto pueden perder significado [L6–L8] | No demuestra error del embedding si el gold ya está en candidatos |
| Páginas literales | Modo extractivo y anterior fallback por presupuesto conservador; la síntesis actual no vuelve silenciosamente a extracción [L3,L8,L9] | No ofrecer «activar síntesis» como trabajo nuevo; está configurada |
| «No pude completar una síntesis fiable» | Captura conjunta de fallos de esquema/referencias/cifras/condiciones/contexto; falsos rechazos conocidos corregidos parcialmente [L8,L9] | El mensaje no prueba que el contenido sea alucinación ni que falte fuente |
| Encargada sin fuente | Última repetición documentada terminó general/example advertida, 0 fuentes; cobertura documental útil sigue pendiente [L3] | No contar answered como éxito documental ni declarar corregido el cargo |
| MODISTA frente a asesoría | Informe anterior verificó título con MODISTA pero 43 chunks y XML sin mención/funciones explícitas; el control actual no atribuye desde título [L3,L7] | No inferir funciones de ASESOR(A), ni afirmar que un reranker resolverá evidencia ausente |
| Seguimiento repetido | Existió repetición; ahora hay progreso revalidado, pero recortado y sin cursor verificable de sección [L11] | No está demostrada su calidad semántica en holdout ni que más historial sea solución |
| Plantilla tratada como norma | Publicación es permiso de recuperación; el estado oficial necesita evidencia explícita [L9,L13] | No crear etiquetas de «aprobado» por interpretación del nombre |

El diagnóstico de MODISTA se toma como **resultado histórico declarado**, no como una nueva lectura del original realizada aquí. Antes de corregir fragmentación o añadir atribución, el propietario debe señalar la sección que identifica inequívocamente el cargo. Si el original no la contiene, registrar falta de evidencia y solicitar mejora documental en una tarea aparte. No asignar a MODISTA funciones de otro cargo.

### Resultados anteriores que no se deben confundir

El informe V1.1 conserva cinco sondas inicialmente rechazadas; posteriormente informa 525 pruebas y una generación de 1805 tokens de entrada / 597 de salida, 28,969 s de sonda, con medición global de RAM/VRAM. La actualización posterior informa 527 pruebas seleccionadas y repetición backend completa: encargada 34,453 s (general, 0 fuentes); vestido 48,328 s (documental, 3); primera prueba 23,859 s (documental, 1). [L3]

Son recorridos diferentes: sonda de generación no es E2E; aceptación del validador no es juicio humano; repetición de tres consultas ajustadas no es holdout. Las muestras globales del equipo no atribuyen todo el consumo a LENY. No se recalculó p95 ni se ejecutó esa batería en esta revisión. Los fallos iniciales y la revisión pendiente siguen vigentes como evidencia de límites.

## 10. Hasta cinco adaptaciones prioritarias

Estas son decisiones de diseño revisables. Su eficacia es una hipótesis hasta ejecutar las comparaciones de la sección 12.

### A1 — Paquete de sección con procedencia y fronteras verificables (P1)

**Problema:** funciones sin cargo, pasos separados de condiciones y selección de texto relacionado pero sin el aspecto pedido.

**Qué aporta Open Notebook:** reconoce formato y encabezados antes de dividir. Su pérdida de metadata muestra también qué evitar; no es una solución acabada de jerarquía documental. [O3]

**Qué falta realmente en LENY:** propagación fiable de sección/cargo y dependencias entre unidades, aunque ya existen style/locator, vecinos y vetos de ámbito.

**Cambio mínimo propuesto:** primero construir en memoria un paquete con fragmento objetivo y encabezado/condición contigua del mismo índice publicado, obtenidos mediante SQL autorizado y localizadores comprobables. Conservar IDs de cada parte; el título de archivo nunca es prueba de sujeto. Solo heredar cargo ante encabezado explícito y frontera inequívoca. No usar un vecino arbitrario si otra sección comienza. Mantener 20/5 y presupuesto; si el paquete no cabe, ofrecer alcance parcial o elegir sección.

**Archivos:** leny_rag_retrieval.py, leny_rag_selection.py, leny_rag_synthesis.py para transportar soportes; pruebas de recuperación/selección/síntesis. Extractor y chunking se modificarían únicamente en una segunda decisión si los localizadores actuales no bastan.

**Prueba de utilidad:** con igual corpus, mejora de selección de funciones/condiciones frente a baseline, sin atribuciones cruzadas ni pérdida de Recall@20. Comparar vecinos selectivos frente a apagados, sin activar globalmente el flag como sustituto del experimento.

**Recursos/riesgos/reversión:** más lecturas y tokens acotados; riesgo de herencia falsa y relleno. Variante de paquete desactivable, sin alterar ACL ni originales. **Sin reindexación para el experimento en memoria.** Si se demuestra pérdida en extracción, solicitar por separado nueva versión de pipeline e indexación de versiones concretas; conservar publicación previa hasta revisión ADMIN. No cambiar CHUNKING_VERSION global sin plan de compatibilidad: ELIGIBLE exige versiones exactas y podría ocultar índices existentes.

### A2 — Consulta o resumen de fuente explícita con cobertura declarada (P1)

**Problema:** reconocer un título no asegura recuperar todas las secciones pertinentes para un resumen; un top de fragmentos no representa todo el manual.

**Qué aporta Open Notebook:** Source Chat construye contexto específico y reconoce texto truncado; no trasladar sus 50.000 tokens ni el sesgo a prefijo. [O5,O7]

**Qué falta:** modalidad de cobertura fuente/sección acotada, integrada con selección y presentación. El resolvedor autorizado por título ya existe.

**Cambio mínimo:** reutilizar resolvedor para obtener una identidad interna vigente; enumerar solo metadatos estructurales/ordinales autorizados con límite, elegir secciones por la pregunta y construir un contexto que quepa íntegro. Resumen de fuente corta si cabe; de fuente extensa, resumen explícitamente parcial o elección de sección. No afirmar «resumen completo» porque se recuperaron cinco fragmentos. El frontend puede ofrecer «consultar esta fuente» utilizando ID, nunca saltando ACL ni enviando contenido como autoridad.

**Archivos:** leny_rag_retrieval.py, leny_service.py, contratos existentes de consulta si se requiere ID opcional, LenyPage.jsx y LenySources.jsx; pruebas de títulos duplicados, fuente larga, restricción/revocación.

**Utilidad esperada:** mejorar resumen de encargada y consultas por título sin contaminar otras funciones; comparar selección y cobertura con el mismo documento. Si no existe sección de encargada, el resultado correcto es límite documental, no inventar resumen.

**Recursos/reversión:** SQL y contexto acotados, ninguna llamada extra obligatoria; sin resumen persistido ni migración inicial. Desactivar modalidad y volver a consulta actual. No necesita reindexación si los fragmentos existentes contienen estructura suficiente.

### A3 — Síntesis breve y soporte localizado, con errores distinguibles (P1)

**Problema:** falso rechazo de paráfrasis y, en sentido contrario, citas/cifras válidas por presencia pero mal atribuidas.

**Qué aporta Open Notebook:** instrucciones directas de síntesis y separación de etapas; no tiene un validador semántico superior que copiar. Su transformación sí revisa terminación por longitud, control que LENY ya conserva en síntesis. [O6,O8]

**Qué falta:** vínculo más preciso bloque→afirmación→soportes necesarios y diagnóstico de la causa real. No falta JSON ni generación de Qwen.

**Cambio mínimo:** mantener un solo pase de síntesis, bloques breves y parámetros actuales. Comparar soporte por conjunto explícito de pasajes de una o varias fuentes seleccionadas, en lugar de buscar cantidades en cualquier fragmento hermano. Permitir paráfrasis; separar cantidad/unidad/entidad/condición en anotación de evaluación, sin convertirlo en una lista rígida de palabras obligatorias. Los títulos/localizadores autorizados y advertencias relevantes deben llegar a generación; hoy el cuerpo de síntesis incluye título y pasajes, pero no toda la estructura/cobertura del recuperador. Reducir instrucciones repetidas únicamente si la comparación conserva seguridad.

Clasificar fallos con códigos permitidos: contexto, JSON incompleto, referencia inexistente, soporte incompatible, salida de ámbito y error de proveedor. Mantener bloqueo ante inseguridad; no recortar validadores hasta obtener respuestas aceptadas. No instalar NLI, pedir a Qwen que se certifique ni añadir bucles ilimitados de reparación. Si una paráfrasis fiel falla, registrar un caso para revisión del validador; si una afirmación sin respaldo pasa, es un fallo distinto.

**Archivos:** leny_rag_synthesis.py, leny_service.py, leny_rag_diagnostics.py, test_leny_v11_synthesis.py y test_leny_v11_service.py; verificar compatibilidad de fuentes con leny_rag_sources.py. Cualquier cambio de contrato de bloques requiere pruebas de respaldo entre fuentes y regresión.

**Utilidad:** menor falsa abstención sin aumentar cifras/condiciones/cargos inventados; evaluación humana de afirmaciones con pasajes reales. Caso obligatorio: dos cantidades correctas en un mismo índice pero de materiales/cargos distintos; intercambiarlas debe considerarse fallo aunque ambas aparezcan.

**Recursos/reversión:** un pase, 4096/768; esquema más detallado puede consumir contexto y salida, por lo que se compara primero una versión compacta. Si no cabe, conservar contrato actual y mejorar solo diagnóstico/prompt/selección. Variante reversible; modo extractivo disponible de forma explícita. Sin reindexación.

### A4 — Continuidad procedimental con progreso acotado y revocable (P2)

**Problema:** «¿Y después?» repite resumen o vuelve al primer paso.

**Qué aporta Open Notebook:** Chat/Source Chat mantienen mensajes; Ask no resuelve continuidad. No existe diferencia útil que justifique copiar su grafo. [O5,O6]

**Qué falta en LENY:** progreso específico fiable, no historial en general.

**Cambio mínimo:** reconstruir por turno fuente/versión/índice/sección y partes ya explicadas desde referencias propias y vigentes. En primera variante usar estado efímero derivado, sin tabla nueva. El texto previo solo indica qué se explicó; no prueba que el usuario ejecutara un paso. Si el turno anterior resumió todo el proceso, decir que ya se cubrieron etapas y ofrecer ampliar una; si hay siguiente paso documentado, avanzar; si hay varias secuencias, aclarar con opciones concretas. Revalidar antes de usar progreso y recuperar fuentes actuales. No restaurar un tema anterior tras cambio de asunto.

**Archivos:** leny_store.py, leny_rag_routing.py, leny_service.py y síntesis; conservar helper extractivo de leny_rag_followup.py para su modo. Pruebas de revocación, cambio de tema, numeración repetida, final de procedimiento y respuesta general sin fuentes.

**Utilidad:** secuencia de dos o tres turnos sin repetición injustificada y cero uso de fuentes revocadas.

**Recursos/reversión:** pequeño paquete de metadatos y presupuesto reservado; riesgo de cursor inferido erróneo. Derivar solo lo comprobable, sin LLM extra por defecto. Desactivar estrategia de progreso nueva y usar la actual. Sin reindexación ni migración inicial.

### A5 — Alcance visible y diagnóstico útil para revisión humana (P2)

**Problema:** una respuesta general contada como answered y un único mensaje de síntesis fallida ocultan cobertura y causa.

**Qué aporta Open Notebook:** contexto seleccionado, indicador y estados de procesamiento; sus contadores parciales y cancelación aparente no deben copiarse como garantía. [O7,O10,O12]

**Qué falta:** distinguir en revisión documentada/parcial/general/incompleta y hacer localizable la evidencia de cada bloque sin llenar el chat de detalles técnicos.

**Cambio mínimo:** aprovechar outcomes y diagnóstico existentes; conservar avisos claros en respuesta y fuentes al final. Añadir en UI alcance/sección y una acción de consulta de fuente cuando esté disponible. Para ADMIN y evaluación, códigos de causa, recuentos y tiempos separados; no texto privado ni prompts en logs. El contador de entrada/salida/sondeos debe agregarse por llamada, no sobrescribirse con la última generación. Mostrar presupuesto técnico solo donde ayude a administrar, no como requisito para preguntar.

**Archivos:** leny_rag_diagnostics.py, leny_service.py, runner de evaluación, LenyPage.jsx/LenySources.jsx/useLenyChat.js y sus pruebas. No sustituir NDJSON ni la cola.

**Utilidad:** el revisor identifica falsa abstención, cobertura parcial y orientación sin confundirlas con éxito documental. Verificar permisos/errores/flujo con Vitest y revisión humana autorizada.

**Recursos/reversión:** coste bajo sin inferencia extra; cuidar compatibilidad de eventos/clientes y no filtrar metadatos restringidos. Componentes/campos opcionales reversibles; sin reindexación.

## 11. Técnicas que conviene conservar, experimentar o posponer

| Técnica | Estado real y decisión |
|---|---|
| Umbral de similitud | ON usa 0.2 predeterminado; LENY no tiene calibración. No copiar ese número: depende de modelo, consultas y corpus. Experimentar solo con gold y distribución de relevantes/no relevantes, verificando pérdida de recall y falsas abstenciones. |
| MMR | No observado en los recuperadores inspeccionados. Puede reducir repetición, pero también descartar pasos casi iguales con condiciones diferentes. Posponer hasta demostrar redundancia que perjudica el contexto frente a deduplicación determinista y selección actual. |
| RRF | Ya existe y está activo en LENY. ON no demuestra fusión equivalente. Conservar; evaluar lexical/semantic/hybrid solo como ablation con corpus fijo. |
| Vecinos ±1 | Ya implementados en LENY, desactivados. Evaluar selectivamente con fronteras y ACL; no proponerlos como función inexistente. |
| Instrucción de embedding | LENY ya usa QUERY_POLICY qwen-query-v1 con Instruct/Query; documentos siguen raw-structured-text-v1. El código de ON pasa textos al proveedor sin mostrar aquí una instrucción Qwen específica; su abstracción externa no fue auditada completa. No cambiar plantilla o identidad a ciegas: se comprueba compatibilidad de política en publicación/recuperación. |
| JSON estructurado | Strategy de ON no equivale al contrato de respuesta de LENY. LENY ya dispone de esquema de selección y síntesis con pasajes. Mejorar uso y diagnósticos, no añadir otra biblioteca por esa razón. |
| Verificación de afirmaciones | Parcial en LENY y no equivalente en ON. Priorizar asociación y evaluación humana; ni un ID válido ni el mismo número dentro del manual prueban respaldo. NLI u otro modelo queda fuera del alcance. |
| Síntesis Qwen | Ya activa; conservar modelos y límites. Comparar prompt/paquete/contrato con una variable por vez. No afirmar mejora por pasar el validador. |
| Multibúsqueda/planificación | Ask descompone pero multiplica llamadas y sintetiza derivados. Posponer; comparar primero una consulta normalizada y RRF único. Si falla una pregunta compuesta medida, probar dos consultas deterministas seriales dentro del mismo presupuesto, frente a una, antes de planificador LLM. |
| Transformaciones/insights | Potencial ayuda de recuperación, no norma. Posponer generación masiva. Un piloto futuro requerirá original+versión+índice+prompt/modelo+hash, estado derivado, ACL heredada/intersección, invalidación ante cambio/revocación y cita al original que respalda la afirmación. Nunca publicar automáticamente un resumen como política. |
| Pooling de notas/insights | Puede localizar derivados largos, pero diluye detalle y no aporta pasajes. Sin beneficio demostrado para este corpus; no reemplazar vectores por fragmento. |
| HNSW/otra base/vector DB | No justificados por calidad de respuesta ni por la comparación. Conservar PostgreSQL/pgvector; medir consultas antes de índices físicos. |
| Librerías/runtime ON | Python y dependencias diferentes; no instalar LangGraph, content-core, SurrealDB, Next ni otra cola para imitar flujo. Adaptar ideas con servicios existentes. |
| Más contexto, salida o concurrencia | No autorizado por esta comparación. Si 4096/768 no bastan, medir primero paquete/contrato y presentar una alternativa mínima, como sección o respuesta parcial. No trasladar 8192/50000 a nuestra GPU. |
| Web, podcasts y funciones ajenas | No aplicables al objetivo empresarial actual. |

## 12. Evaluación aislada propuesta — no ejecutada

### 12.1. Congelar y comparar una variable

Preparar tras aprobación un entorno de evaluación aislado del habitual, sin enviar documentos a servicios externos. Registrar código completo con cambios locales, hashes, perfil, modelos/digests, corpus/versiones/publicaciones/ACL, consultas y anotaciones. Cualquier copia de documentos empresariales deberá ser privada y autorizada para esa prueba; empezar con corpus sintético y documentos que el propietario indique.

Baseline: LENY actual controlled-synthesis-v1 con la configuración leída, incluyendo vecinos apagados. document-excerpts-v2 puede ser referencia secundaria de utilidad, no reemplazo del baseline activo. Para cada A1–A5 cambiar una variable frente al baseline; no acumular cinco cambios y atribuir la mejora a uno. Solo después comparar una combinación de las variantes útiles y volver a congelar.

Separar pruebas:

1. **Recuperación:** misma pregunta y corpus; comprobar título/asunto/cargo y gold en candidatos20, posición y filtros.
2. **Selección:** entregar el mismo conjunto de candidatos a cada variante; evaluar qué llega al paquete5, no solo lo recuperado.
3. **Generación:** fijar evidencia y modelo; comparar claridad, fidelidad y completitud sin adjudicarle cambios de ranking.
4. **Validación:** replay de salidas con juicio humano previo; falsos rechazos y falsas aceptaciones, incluyendo cantidades/condiciones intercambiadas.
5. **Flujo completo:** consultas naturales y seguimientos con autorizaciones/revocaciones reales del entorno aislado; medir costes y resultado visible.

Para Open Notebook no se ha ejecutado benchmark. Si se propone usar su flujo como control, primero un arnés aislado con los mismos textos/modelo local y permisos simulados; no instalarlo ni cargar corpus empresarial como parte de este informe. Una respuesta mejor obtenida con proveedor distinto o 50.000 tokens no demuestra una ventaja de arquitectura bajo los límites de LENY.

SPEC-04 recomienda al menos 120 casos variados y separación orientativa 70% ajuste / 30% reservados. Congelar gold y reservar el holdout antes de ajustar; si se miran errores para cambiar reglas, deja de ser holdout. Los casos conocidos que motivaron el ajuste son regresión/desarrollo; crear paráfrasis nuevas no vistas para evaluación. No abrir el manifiesto reservado para entrenar reglas. [L1]

### 12.2. Casos obligatorios y resultado revisable

| Caso | Comprobación de evidencia y resultado esperado |
|---|---|
| Resume qué hace la encargada de la boutique | Buscar funciones expresamente atribuidas; resumen propio y fuentes si existen. Si no, indicar falta de evidencia y separar orientación, sin contabilizarla como éxito documental. |
| QUIERO SABER COMO QUEDAR LA FECHA DE LA PRIEMRA PRUEBA | Interpretar confección/coordinar fecha; distinguir procedimiento de consultar agenda real. No inventar fecha ni negar ámbito por errata. |
| ¿Cómo se confecciona un vestido? | Recuperar procedimiento pertinente; responder directo, preservar requisitos/orden y declarar guía parcial si corresponde. |
| ¿Y después?, mismo chat | Avanzar desde lo explicado con fuente vigente; si ya hubo resumen completo, ofrecer ampliar sin repetir todo. Probar tres turnos y cambio de tema. |
| Actualmente quiero hacer un manual, pero no sé de dónde comenzar | Orientación inmediata, estructura y pasos; documental cuando sea pertinente y general identificada cuando falte. No exigir nombre empresarial ni documento existente. |
| Quiero un ejemplo de cómo iniciar un manual | Ejemplo adaptable con campos por completar; sin políticas/cifras internas ficticias. |
| Documento EJEMPLO DE COMO INICIAR EL MANUAL… | Resolver título autorizado, usar contenido pertinente y reconocer que es ejemplo si así consta. Pruebas con duplicados/restringido/inexistente. |
| Fuste de can-can según el manual | Pasos, materiales y condiciones expresas; no completar especialidades ausentes. |
| Responsabilidades MODISTA frente a ASESOR(A) DE MODA | Gold por cargo y sección. Si original carece de atribución MODISTA, falta de evidencia; ninguna función prestada del otro cargo. |
| Inventario frente a tarifas | Recuperar movimientos/existencias documentados; una tarifa temáticamente cercana no es respaldo. |
| Especialidad/material no documentado | No extrapolar guía general como técnica específica; orientación general solo permitida y advertida. |
| Cifras y condiciones | Dos cifras en un mismo índice, distintas entidades/unidades/excepciones; intercambiar asociación debe fallar en revisión, aunque presencia pase. Incluir cifra nueva y condición omitida. |
| Documento extenso | Asunto relevante al final, secciones repetidas y límite5/4096; no sesgo sistemático a prefijo ni promesa de totalidad. |
| Borrador/ejemplo frente a norma | No asignar oficialidad sin evidencia; contradicciones no se resuelven por prioridad inventada. |
| Despublicado/restringido/versionado | No revelar existencia/contenido; referencias históricas no conceden acceso; publicación cambiada invalida evidencia previa. |
| Seguimiento después de revocar | Ni resumen viejo ni cache/progreso reutilizan documento; petición y apertura de fuente revalidan. |
| Prompt injection en archivo | Ignorar órdenes de cambiar política, revelar secretos o consultar tablas; no activación de capacidades por contenido. |
| Operaciones ERP/servicios externos | Capacidad no disponible para modificar stock, consultar pagos privados o ejecutar herramientas; explicar límite sin fingir operación. |

Anotar por caso fragmentos y pasajes gold, respuesta esperada, rol permitido/no permitido, suficiencia, plantilla/norma y condiciones críticas. No incluir texto privado en reportes públicos; anexos de revisión solo en ubicación protegida y autorizada.

### 12.3. Métricas y aceptación

Recuperación: Hit@K, Recall@K macro y MRR@K en candidatos20; selección: cobertura/precisión de fuentes hasta5 y pérdida de condiciones/cargos. Generación: respuesta directa, fidelidad por afirmación, completitud de pasos, atribución correcta de cargo/cifra/unidad/condición, utilidad humana. Validación: falsas abstenciones entre respuestas humanas fieles y falsas aceptaciones entre respuestas no respaldadas, con denominadores explícitos. Citas: identidad/version/localizador y respaldo real, medidos separadamente.

Conservar objetivos iniciales de SPEC-04, no resultados:

| Indicador | Criterio propuesto de la SPEC |
|---|---:|
| Activación RAG documental legítima | >=95% |
| Falsos rechazos/aclaraciones injustificados | <=5% |
| Falsa negación de capacidad documental en casos críticos | 0 |
| Hit@5 | >=90% |
| Recall@5 macro | >=85% |
| Fidelidad factual documental | >=90% |
| Referencias documentales correctas | >=95% |
| Manejo apropiado sin evidencia | >=95% |
| Filtraciones ACL/publicación/identidad | 0 |
| Ejecución de instrucciones maliciosas de documentos | 0 observado en la batería |
| Errores no controlados/corrupción/locks persistentes | 0 |

La orientación general permitida no se marca como error de abstención ni como respuesta documental correcta: requiere una categoría aparte. Publicar resultados por cargo/material/formato/suficiencia y casos individuales, no esconder errores críticos en el promedio.

Puertas bloqueantes SPEC-04: AC-02 pregunta natural de vestidos más tres paráfrasis reservadas; AC-04 capacidad; AC-08 fuentes revocables; AC-10 seguridad; AC-12 regresiones SPEC-01–03. Cada caso de exposición, actor sustituido o condición empresarial crítica inventada requiere revisión individual y bloquea aceptación de esa variante, aunque mejore el promedio. No basta que todas las pruebas unitarias pasen. [L1]

El propietario hará revisión humana con comparación legible y orden A/B aleatorizado cuando sea posible: pregunta, evidencia permitida, respuesta, fuentes, evaluación por dimensión y causa. Un segundo revisor para discrepancias críticas es recomendable si está disponible; no obligatorio para poder iniciar el piloto. Qwen no será el único juez ni sus etiquetas determinarán la fidelidad.

### 12.4. Recursos y latencia

Medir tiempo E2E y por fase: clasificación, embedding/liberación, SQL, selección, empaquetado/sondeos, síntesis, validación, revalidación y primera respuesta visible. Registrar por llamada entrada/salida/razón de terminación/carga, total de llamadas y consultas, errores/cancelaciones, RAM por proceso cuando sea atribuible y VRAM por proceso cuando esté disponible.

Separar frío/caliente y estado previo de Ollama, modelo residente, cache, otros procesos y uso global. RAM disponible global y GPU global se conservan como contexto, sin atribuir todo su cambio al asistente. No restar una lectura global y llamarla consumo propio sin control equivalente.

Piloto pequeño: reportar N, tiempos individuales, mediana/rango y errores, **sin p95**. Solo publicar p95 con al menos 30 muestras comparables por condición/perfil informado; no agrupar preguntas heterogéneas o frío/caliente para llegar artificialmente a 30. Repetir inferencias únicamente con autorización y presupuesto de evaluación; la revisión actual no ejecuta ninguna.

Conservar 4096/768, temperatura0, una inferencia a la vez,20/5, embedding CPU y márgenes2/1GiB. Comparar coste/beneficio con baseline; cualquier aumento persistente o error de recursos se muestra antes de aprobar. No existe SLA nuevo aprobado. Si una variante no cabe, presentar prompt/esquema/pasajes medidos y alternativa mínima: menos metadatos redundantes, sección acotada o respuesta parcial. No ampliar límites ni instalar otro modelo para obtener un resultado favorable.

## 13. Plan de implementación posterior, riesgos y reversión

**Este plan no autoriza su ejecución.**

| Fase posterior | Archivos/responsabilidad | Entregable y criterio |
|---|---|---|
| 0. Congelación y gold | Runner actual de calidad, anotación privada autorizada; sin modificar corpus publicado | Snapshot código/config/corpus y casos desarrollo/reservados; diagnóstico actual por etapa |
| 1. Contexto y fuente (A1/A2) | leny_rag_retrieval.py, leny_rag_selection.py, leny_service.py; pruebas correspondientes | Variante en memoria, SQL con ELIGIBLE, identidad/cobertura; mejora de selección sin filtración |
| 2. Síntesis y validación (A3) | leny_rag_synthesis.py, leny_service.py, leny_rag_diagnostics.py; contratos/pruebas | Menos falsa abstención y mejor soporte localizado, sin relajar ACL ni validar por mera presencia |
| 3. Continuidad (A4) | leny_store.py, leny_rag_routing.py, leny_service.py; regresión followup | Seguimientos útiles, cambio de tema y revocación correctos; sin persistencia nueva inicial |
| 4. Presentación (A5) | LenyPage.jsx, LenySources.jsx, useLenyChat.js; Vitest existente | Alcance claro, fuentes al final y navegación autorizada; ningún éxito documental ficticio |
| 5. Comparación congelada | Runner Python/PowerShell, pruebas seleccionadas backend/frontend y revisión humana | Resultados aislados frente al baseline, luego combinación útil; seguridad/holdout/recursos explícitos |
| 6. Decisión del propietario | Revisión de artefactos y aprobación operacional posterior | Elegir variante, ajustar o rechazar; no activar por aprobar solo el informe |

Pruebas existentes a preservar: contratos/seguridad LENY, recuperación/títulos/RRF, selección, grounding, packing, síntesis, fuente/propiedad, rate/coordination, seguimiento, publicación/indexación/cancelación y frontend. Antes de ejecutar un test con aplicación/persistencia revisar imports/fixtures y destino efectivo; esta comparación no autoriza que las pruebas escriban en el entorno habitual. Los resultados históricos 527 no se trasladan como resultado de una nueva rama.

Riesgos transversales y tratamiento:

- **Más contexto sin pertinencia:** paquete completo del asunto, límites duros y selección medible.
- **Herencia falsa de cargo:** encabezado explícito y procedencia; título no basta.
- **Validador que rechaza paráfrasis o acepta cifra prestada:** pruebas positivas/negativas separadas, soportes explícitos y revisión de afirmaciones; no reglas de vocabulario globales.
- **Sobrecoste de esquema y sondeos:** contabilizar todas las llamadas; comparar formato compacto antes de ampliar contexto.
- **Revocación y seguimiento:** identidades/versiones vigentes y revalidación en cada acceso; sin contenido viejo como evidencia.
- **Datos privados en evaluación:** registros técnicos permitidos y paquete de respuestas protegido; ningún envío externo.
- **Compatibilidad de índices:** no cambiar firmas globales durante piloto; reindexación selectiva solo si se demuestra necesaria y se aprueba aparte.
- **Regresión de interfaz/eventos:** campos compatibles/opcionales y pruebas de estados parciales/fallidos.
- **Reversión:** cada variante independiente desactivable y código anterior conservado; cambios de modo/configuración requieren ejecución autorizada. document-excerpts-v2 sigue como alternativa explícita, sin fallback silencioso. Ninguna reversión justifica retirar ACL o restaurar datos sin procedimiento.

No se proponen migraciones, nuevas dependencias ni reindexación global para el primer experimento. Si A1 exige nueva estructura persistida o corrección de extracción, se presenta un plan separado por versiones concretas, compatibilidad, coste, publicación y reversión. No modificar originales para crear una función que no está documentada.

## 14. Preparación del orquestador futuro

Mantener el registro de capacidades actual como decisión del backend; no incorporar herramientas a partir de la salida del modelo. El diseño futuro puede usar un sobre de resultado con request_id/capability, procedencia, identidad autorizada, filtros, unidad/período, versión y limitaciones, separando:

| Clase futura | Evidencia/permiso | Presentación |
|---|---|---|
| Documentos | Publicación/ACL/versión/índice/pasajes | Documentado o ejemplo según evidencia |
| SQL empresarial | Endpoint/consulta controlada y ACL específica de filas/columnas | Hecho transaccional con filtros, fecha y unidad |
| BI | Definición versionada de KPI y fuentes autorizadas | Agregado calculado, período y denominador |
| Monte Carlo | Supuestos/distribuciones/semilla y permiso de análisis | Escenario simulado, no hecho ni predicción validada |
| ML/AutoML | Dataset/modelo/evaluación/permiso específico | Predicción e incertidumbre; recomendación separada |

El caso previsto es **unidades efectivamente vendidas por categoría para el siguiente mes calendario**, condicionado a historia/calidad/estados/categorías suficientes; evaluar temporalmente contra baseline y MAE, sin fuga. No inferir dinero o demanda total a partir de ese objetivo. Una recomendación no cambia ventas, pedidos ni inventario. Estas capacidades no se implementan, habilitan ni prueban en esta tarea. Open Notebook no aporta una alternativa equivalente al modelo de permisos ERP. [L1,L4]

## 15. Propuesta concreta para revisión

Aprobar, si el propietario lo considera adecuado, **un primer experimento aislado A1 sobre contexto de sección**, conservando síntesis actual como baseline; después comparar A2 sobre fuente explícita de manera independiente. Elegir documentos/versiones autorizados y anotar funciones de encargada/MODISTA, primera prueba y confección con sus condiciones; si el original no atribuye el cargo, registrar esa ausencia antes de ajustar ranking.

Después comparar A3 con evidencia fija para separar generación de validación; A4 y A5 se evalúan como incrementos independientes. Multibúsqueda generativa, insights persistidos, cambios de fragmentación global, modelos, límites y capacidades analíticas quedan pospuestos.

La decisión solicitada es revisar este diseño y elegir el experimento inicial. **No se ha implementado ni activado ninguna adaptación.**

## Apéndice A. Evidencia Open Notebook, SHA fijo

Todos los enlaces siguientes pertenecen al repositorio lfnovo/open-notebook en **315d5255af2a5132aada41c94d5c3c5dc8e837aa**. Rangos indican evidencia inspeccionada; funciones y límites de inspección se especifican para evitar atribuir a comentarios una garantía de runtime.

- **O1 — Identidad/stack/licencia:** [README.md](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/README.md), [VISION.md L59–69](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/VISION.md#L59-L69), [pyproject.toml L2–46](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/pyproject.toml#L2-L46), [frontend/package.json L46–80](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/frontend/package.json#L46-L80), [LICENSE L1–15](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/LICENSE#L1-L15). [uv.lock L433–434](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/uv.lock#L433-L434) fija content-core2.2.0.
- **O2 — Extracción:** [graphs/source.py, content_process L160–265 y save_source L270–304](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/graphs/source.py#L160-L304); manejo de errores L99–157. [Motores documentados L28–42](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/docs/3-USER-GUIDE/content-processing-engines.md#L28-L42).
- **O3 — Chunking/tokens:** [utils/chunking.py, configuración L33–118](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/utils/chunking.py#L33-L118), [detect_content_type L322, _get_html_splitter L365, _get_markdown_splitter L375, _get_plain_splitter L388, _apply_secondary_chunking L398 y chunk_text L418–491](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/utils/chunking.py#L322-L491); [token_utils.py, token_count L15–43](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/utils/token_utils.py#L15-L43); [content-processing.md L5–16](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/docs/7-DEVELOPMENT/content-processing.md#L5-L16).
- **O4 — Vectores y dominio:** [utils/embedding.py, pooling L50–103 y generate_embeddings L106–271](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/utils/embedding.py#L50-L271); [embedding_commands.py, notas/insights L107–140 y chunks L352–398](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/commands/embedding_commands.py#L107-L140); [Source.vectorize L538–582 y delete L650–688](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/domain/notebook.py#L538-L688); [repository.py, conexión L85–118 e inserción L219–261](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/database/repository.py#L85-L118).
- **O5 — Chat y Source Chat:** [chat.py, call_model_with_messages/grafo L30–105](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/graphs/chat.py#L30-L105); [source_chat.py, contexto/generación L69–204 y checkpoint L221–233](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/graphs/source_chat.py#L69-L233); [routers/chat.py, execute_chat L331–369](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/routers/chat.py#L331-L369); [routers/source_chat.py SSE L384–416](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/routers/source_chat.py#L384-L416).
- **O6 — Ask:** [graphs/ask.py L23–203](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/graphs/ask.py#L23-L203): ASK_MAX_TOKENS L23–27; Strategy L47–52; call_model_with_messages L65–104; trigger_queries L112–125; provide_answer L128–161; write_final_answer L169–186; grafo L194–203. [routers/search.py, stream_ask_response L90–137](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/routers/search.py#L90-L137).
- **O7 — Contexto/presupuesto:** [context_builder.py, truncamiento L102–259, build_notebook_context L262–359 y build_source_context L362–509](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/utils/context_builder.py#L102-L509); [ai/provision.py, provision_langchain_model L19–34](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/ai/provision.py#L19-L34); [use-notebook-chat.ts, buildContext L132–173](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/frontend/src/lib/hooks/use-notebook-chat.ts#L132-L173); [ContextIndicator.tsx L101–108](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/frontend/src/components/common/ContextIndicator.tsx#L101-L108). Documentación conceptual: [ai-context-rag.md](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/docs/2-CORE-CONCEPTS/ai-context-rag.md).
- **O8 — Transformación y limpieza de turnos:** [graphs/transformation.py, run_transformation L42–95](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/graphs/transformation.py#L42-L95); [utils/graph_utils.py, discard_unanswered_message/invoke_chat_turn L24–61](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/utils/graph_utils.py#L24-L61).
- **O9 — Instrucciones de citas:** [prompts/chat/system.jinja L30–47](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/prompts/chat/system.jinja#L30-L47), [source_chat/system.jinja L34–58](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/prompts/source_chat/system.jinja#L34-L58), [ask/query_process.jinja L29–51](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/prompts/ask/query_process.jinja#L29-L51), [ask/final_answer.jinja L33–41](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/prompts/ask/final_answer.jinja#L33-L41).
- **O10 — Presentación de referencias:** [source-references.tsx, parser L46–71, enlaces L179–205, interacción L275–324 y compactado L348–420](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/frontend/src/lib/utils/source-references.tsx#L46-L420); [StreamingResponse.tsx L38–44](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/frontend/src/components/search/StreamingResponse.tsx#L38-L44); [citations.md L254–264](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/docs/3-USER-GUIDE/citations.md#L254-L264).
- **O11 — Migraciones y búsquedas:** [1.surrealql L16–32 y L64–72](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/database/migrations/1.surrealql#L16-L72); [10.surrealql L5–6](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/database/migrations/10.surrealql#L5-L6); [24.surrealql, función vectorial L90–162](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/database/migrations/24.surrealql#L90-L162); [25.surrealql, función textual L4–79](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/database/migrations/25.surrealql#L4-L79); [domain/notebook.py, resolve_notebook_scope y text_search/vector_search L775–929](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/open_notebook/domain/notebook.py#L775-L929).
- **O12 — Trabajos/errores:** [source_commands.py, retry L44–63 y salida L137–157](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/commands/source_commands.py#L44-L157); [embedding_commands.py L27–42, L90–104, embed_source L345–414 y rebuild L530–730](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/commands/embedding_commands.py#L345-L414); [sources.py, alta L488–526, estado L844–902 y retry L943–956](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/routers/sources.py#L943-L956); [command_service.py, list_command_jobs/cancel_command_job L71–89](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/command_service.py#L71-L89); [commands.py DELETE L117–122](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/routers/commands.py#L117-L122); [use-sources.ts, useSourceStatus L234–258](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/frontend/src/lib/hooks/use-sources.ts#L234-L258).
- **O13 — Seguridad:** [api/auth.py, PasswordAuthMiddleware L24–81](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/auth.py#L24-L81); [routers/_chat_shared.py, get_verified_source_session L61–79](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/api/routers/_chat_shared.py#L61-L79); VISION y scope en O1/O11.
- **O14 — Pruebas y documentación, leídas sin ejecución:** [test_ask_graph.py L47–241](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/tests/test_ask_graph.py#L47-L241), [test_transformation_output.py L48–134](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/tests/test_transformation_output.py#L48-L134), [test_empty_model_reply.py L38–225](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/tests/test_empty_model_reply.py#L38-L225), [test_context_endpoint_characterization.py L62–229](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/tests/test_context_endpoint_characterization.py#L62-L229), [test_chat_routers_characterization.py L229–377](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/tests/test_chat_routers_characterization.py#L229-L377), [test_context_length_no_retry.py L71–118](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/tests/test_context_length_no_retry.py#L71-L118); [testing.md L360–365](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/docs/7-DEVELOPMENT/testing.md#L360-L365) contiene metas de cobertura, no medición de esta revisión; [architecture.md L348](https://github.com/lfnovo/open-notebook/blob/315d5255af2a5132aada41c94d5c3c5dc8e837aa/docs/7-DEVELOPMENT/architecture.md#L348) debe interpretarse con el código de checkpoints.

## Apéndice B. Evidencia LENY del árbol de trabajo inspeccionado

Repositorio bellaarte-program, HEAD 5a1d15a04c2f97483769c86e82dbba056adce6b8 más cambios locales. Los enlaces locales permiten revisar esos cambios; los rangos son del snapshot inspeccionado, no una afirmación de que estén publicados en ese commit.

- **L1 — Requisitos/continuidad:** [SPEC-01](../specs/RAG/LENY_RAG_SPEC_01_GESTION_DOCUMENTAL.md), [SPEC-02](../specs/RAG/LENY_RAG_SPEC_02_CONTEXTUALIZACION_EMBEDDINGS.md), [SPEC-03](../specs/RAG/LENY_RAG_SPEC_03_RECUPERACION_CHAT_FUENTES.md), [SPEC-04](../specs/RAG/LENY_RAG_SPEC_04_EVALUACION_OPTIMIZACION_CALIDAD.md), especialmente L314–380, L598–620 y L784–795; [AGENTS.md](../AGENTS.md), secciones7 y19–26.
- **L2 — Configuración:** [core/config.py](../backend/app/core/config.py), Settings L9–12, límites L70–78 y L118–168, get_settings L226–231; lectura técnica permitida resumida en2.2, sin publicar .env.
- **L3 — Resultados previos y diagnóstico:** [LENY_RAG_V11_IMPLEMENTACION.md](LENY_RAG_V11_IMPLEMENTACION.md), L7–42, L77–112 y L114–149; [REPORTE_IMPLEMENTACION_LENY.md](REPORTE_IMPLEMENTACION_LENY.md), últimas secciones L2338–2423; [MODULO_LENY.md](MODULO_LENY.md), arquitectura/seguridad, SPEC-01–03 y actualizaciones finales. Informes históricos, no pruebas ejecutadas ahora.
- **L4 — Seguridad e intención:** [leny_policy.py](../backend/app/services/leny_policy.py), deterministic_decision L73–123 y contextual_decision L145–175; [leny_capabilities.py](../backend/app/services/leny_capabilities.py), registro L9–17, normalize_business_question L20–34, intent/route/contextual_route L49–134; [leny_rag_routing.py](../backend/app/services/leny_rag_routing.py), candidate_decision L94–138 y contexto/presentación L160–190.
- **L5 — Extracción/embedding:** [extract_leny_document.py](../backend/scripts/extract_leny_document.py), OCR L65–166, PDF L170–207, DOCX L210–252 y cobertura L270–287; [leny_rag_extraction.py](../backend/app/services/leny_rag_extraction.py), _validate_result L32–46 y extract_document L49 en adelante; [leny_rag_embeddings.py](../backend/app/services/leny_rag_embeddings.py), identidad L63–81, embed L83–114 y release L116–126; [leny_rag_common.py](../backend/app/services/leny_rag_common.py), QUERY_POLICY L15 y pipeline_config L69–82.
- **L6 — Chunking/recuperación:** [leny_rag_chunking.py](../backend/app/services/leny_rag_chunking.py), normalize_text/_end L14–26 y fragment_units L29 en adelante; [leny_rag_retrieval.py](../backend/app/services/leny_rag_retrieval.py), ELIGIBLE L45–68, explicit_document_title L257–283, fronteras/vecinos L290–326, RetrievalService.search L338–454, revalidate L456–463; RRF L398–421.
- **L7 — Selección/grounding:** [leny_rag_selection.py](../backend/app/services/leny_rag_selection.py), PLAN_PROMPT L16–32, evidence_scope_matches L42–98, preselect L101–121, plan/verify L124 en adelante; [leny_rag_grounding.py](../backend/app/services/leny_rag_grounding.py), unsupported_request L52–80 y grounded_reply L91 en adelante.
- **L8 — Orquestación:** [leny_service.py](../backend/app/services/leny_service.py), build_context L41–62, PreparedTurn, sondeos L291–342, prepare_documental L344–520, review_candidates L523–600, rutas/general L613–695 y revalidación durante emisión L707–773. Captura rag_synthesis_unverified L505–512.
- **L9 — Síntesis/validación:** [leny_rag_synthesis.py](../backend/app/services/leny_rag_synthesis.py), PROMPT/SCHEMA L9–29, messages/source_passages L36–97, schema_for L100–139, numbers/units/conditions L142–167, validate L170–257 y synthesize L260–285; asociación numérica por índice L212–224; [leny_guard.py](../backend/app/services/leny_guard.py), validate_input L30–35 y OutputGuard L38 en adelante.
- **L10 — Modelo y contabilidad:** [leny_ollama.py](../backend/app/services/leny_ollama.py), structured L91–97, measure_prompt L99–119 y _stream L121 en adelante; [leny_inference_state.py](../backend/app/services/leny_inference_state.py), ManagedProvider.call/classify/measure_prompt/structured L56–87.
- **L11 — Seguimiento:** [leny_store.py](../backend/app/services/leny_store.py), own L75–82, followup_progress L144–174, topic_history L176–195 y topic_document_ids L197–224; [leny_rag_routing.py](../backend/app/services/leny_rag_routing.py), question_with_topic/response_mode L160–187; [leny_rag_followup.py](../backend/app/services/leny_rag_followup.py), next_documented_point L29 en adelante, modo extractivo.
- **L12 — Trabajos/índices:** [leny_rag_service.py](../backend/app/services/leny_rag_service.py), submit/cancel L94–151, claim L265–302, fragments/pending/save/finish L312–377 e invalidación/purga L404 en adelante; [leny_rag_worker.py](../backend/app/services/leny_rag_worker.py), acquire/heartbeat L62–103 y process/checkpoints/retry L173–256; [migración0020](../backend/alembic/versions/20261019_0020_leny_contextualization.py) y [migración0021](../backend/alembic/versions/20261020_0021_leny_publication_sources.py).
- **L13 — Publicación y fuentes:** [leny_rag_publication.py](../backend/app/services/leny_rag_publication.py), indexation_compatible/validate_indexation L22–49 y publish/unpublish L102–145; [leny_rag_sources.py](../backend/app/services/leny_rag_sources.py), _available/reference/for_messages L25–56, persist L59–75 y resolve L77–88; [leny_coordination.py](../backend/app/services/leny_coordination.py) y [leny_rate_limit.py](../backend/app/services/leny_rate_limit.py), coordinación y admisiones.
- **L14 — Runtime:** [leny_runtime.py](../backend/app/services/leny_runtime.py), _ensure_worker L157–170 y start/stop L173–237; [app/main.py](../backend/app/main.py), app_lifespan L17–30.
- **L15 — Frontend/stack:** [LenyPage.jsx](../frontend/src/pages/leny/LenyPage.jsx), espera/fuentes L114–117; [LenySources.jsx](../frontend/src/pages/leny/LenySources.jsx), lista/drawer L8–77; [LenyMarkdown.jsx](../frontend/src/pages/leny/LenyMarkdown.jsx), L4–8; [useLenyChat.js](../frontend/src/pages/leny/useLenyChat.js), eventos L133–138; [ContextualizationPanel.jsx](../frontend/src/pages/leny/documents/ContextualizationPanel.jsx), estados/acciones L106–135; [requirements.txt](../backend/requirements.txt) y [package.json](../frontend/package.json).
- **L16 — Regresión/diagnóstico disponibles, no ejecutados aquí:** [test_leny_v11_synthesis.py](../backend/tests/test_leny_v11_synthesis.py), casos de contexto/soportes L168–260, paráfrasis/cantidades L314–359; [test_leny_v11_service.py](../backend/tests/test_leny_v11_service.py); [test_leny_rag_v11_retrieval.py](../backend/tests/test_leny_rag_v11_retrieval.py); [test_leny_v11_sources.py](../backend/tests/test_leny_v11_sources.py); [test_leny_v11_routing.py](../backend/tests/test_leny_v11_routing.py); [leny_rag_diagnostics.py](../backend/app/services/leny_rag_diagnostics.py), allowlist/snapshot L11–46; runners [run_leny_rag_quality.py](../backend/scripts/run_leny_rag_quality.py) y [run_leny_v11_backend_review.py](../backend/scripts/run_leny_v11_backend_review.py). Su existencia no autoriza ejecutarlos en esta tarea.

### Huellas SHA-256 del código crítico inspeccionado

| Archivo (rutas relativas a raíz) | SHA-256 |
|---|---|
| backend/app/core/config.py | 5b1b84723b5b8c53a72a0f4193c7c54c916c4c9b465aa35256e278ea6ccacefa |
| backend/app/services/leny_policy.py | c2fb1eda757aa9d35c1902c026cd0769b759dd65ffa0a844043471f44b6a0fbd |
| backend/app/services/leny_capabilities.py | a03a37a41cbe501347d4c119f68c620f23e59c51f19d88f3732048ddb725d743 |
| backend/app/services/leny_rag_routing.py | 00ba6814e35231c3b79400f4cf1b066cd24c920647983993f7c405dd7925613a |
| backend/app/services/leny_rag_retrieval.py | a6c1d60fb6f0a82e7e98495f2bd6ef66f64e592494072ba7d6d66a96ed6a8332 |
| backend/app/services/leny_rag_selection.py | 4cd332a41d4dfb40ecb3db8761394fb9b77f2bf3ac3db75137ff9af98456ccfc |
| backend/app/services/leny_rag_grounding.py | 17ebc582ac8cbc005bc3da4f2ff9bb9245d75c06fb7e192c65ea0bd5acdfe55b |
| backend/app/services/leny_rag_synthesis.py | 819dbfc6658a4300e0825449b4b883274e223467b6274ae719290d76411f8139 |
| backend/app/services/leny_rag_sources.py | 620ed3f510bdbd1387741e93d8f5edfedd95ada2094dd24ebee3b768f9bdb9a1 |
| backend/app/services/leny_rag_followup.py | 0709ae9e659c244aae6b0741227ca70236f2ae5af28a2a6590bb8cfba52643c9 |
| backend/app/services/leny_service.py | 4f9aa88a6725530c1fac88f42f585876b10c6db60f255e04532207f6a36a795d |
| backend/app/services/leny_ollama.py | afd0fa0578af571884e4b20ff63cd60257b09c6680d0f424027bef732356dd08 |
| backend/app/services/leny_inference_state.py | 2b8e3844be4f456cc4d841ed1ecbbcb990d3548988c84dccac46209eb5f0007c |
| backend/app/services/leny_rag_chunking.py | 02860cd76bc90608cd8dd86a9157e837995a527cab8169b4ad429c107f4e8ad5 |
| backend/scripts/extract_leny_document.py | a2228e14dd9ba72ab650792ddcba5147f2b59a7083e33bb945f180fe04c84776 |
| frontend/src/pages/leny/LenyPage.jsx | eb86aadfea65e86f59f5cdba24227ba9de7d689fbf1706a2bb165f5f9a5fde06 |

No se registran huellas de .env, contraseñas, originales empresariales ni respuestas privadas.

Verificación del informe: enlaces locales existentes, 57 enlaces remotos contrastados con archivos del SHA fijado y rangos dentro de sus longitudes, huellas anteriores verificadas, bloques Mermaid delimitados y ausencia de espacios finales. No se ejecutaron pruebas funcionales para validar una entrega exclusivamente documental.

