# GestorEstado (F3.2)

> Módulo: `dm_agent.estado.gestor` · Fase: F3.2

Persistencia JSON de los esquemas de F3.1 (`Ficha`, `EstadoPartida`) con
escritura atómica y snapshots opcionales. **No** hay todavía tools de
ficha/HP/XP, combate, inventario rico, mundo, misiones, RAG ni memoria
narrativa: esto es solo la capa de guardado/carga.

## Estructura de carpetas

La raíz se toma de `config/proyecto.json → rutas.storage` (por defecto
`./storage`). Por campaña:

```text
<storage>/
└── campañas/
    └── <campaña_id>/
        ├── estado_partida.json
        ├── fichas/
        │   └── <personaje_id>.json
        └── snapshots/            (solo si snapshots=True)
            ├── estado_partida_<ts>.json
            └── ficha_<personaje_id>_<ts>.json
```

## Formato JSON

Cada fichero es el `model_dump_json(indent=2)` del esquema correspondiente, con
`version_schema`. Ver `docs/esquemas/ficha.md` y `docs/esquemas/estado_partida.md`.

## Escritura segura (atómica)

Para no dejar JSON corrupto si el proceso se interrumpe:

1. se serializa el modelo y se verifica que es JSON válido;
2. se escribe en un fichero temporal `*.tmp` en el **mismo** directorio (con
   `flush` + `fsync`);
3. se hace `os.replace(tmp, destino)` (renombrado atómico en el mismo sistema de
   ficheros).

Si algo falla antes del `replace`, el temporal se borra y el destino anterior
queda intacto.

## Snapshots

El gestor se construye con `GestorEstado(raiz, snapshots=False)`. Si
`snapshots=True`:

- antes de **sobrescribir** `estado_partida.json` o una ficha existente, se copia
  el fichero **anterior** a `snapshots/` con un timestamp UTC seguro para nombre
  de fichero (`%Y%m%dT%H%M%S_%fZ`);
- si no existía fichero previo, **no** se crea snapshot.

## Errores

```text
ErrorEstado              (base)
├── ErrorEstadoNoEncontrado   el fichero/campaña/ficha no existe
└── ErrorEstadoInvalido       JSON inválido o que no cumple el esquema
```

## API

```python
GestorEstado(raiz_storage, snapshots=False)
  .ruta_campaña(campaña_id) -> Path
  .existe_campaña(campaña_id) -> bool
  .crear_campaña_si_no_existe(campaña_id) -> Path
  .guardar_ficha(campaña_id, ficha) -> Path
  .cargar_ficha(campaña_id, personaje_id) -> Ficha
  .listar_fichas(campaña_id) -> list[str]
  .guardar_estado_partida(estado) -> Path        # usa estado.campaña_id
  .cargar_estado_partida(campaña_id) -> EstadoPartida
```

## Limitaciones

- Solo persiste `Ficha` y `EstadoPartida`. No hay inventario complejo, combate,
  mundo, misiones, RAG ni memoria narrativa.
- No hay todavía tools que el LLM pueda invocar para leer/escribir estado (F3.3+).
- No hay bloqueo de concurrencia (un único proceso de juego por campaña).
- El `Evento` auditable y su log JSONL llegan en F3.5.
