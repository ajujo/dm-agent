# Modelos locales — recomendaciones iniciales

> Hardware del usuario: **RTX 5090 (24+ GB VRAM)** + **Mac Studio M2 Ultra (128 GB unified RAM)**.

## Filosofía

dm-agent debe usar **al menos dos endpoints simultáneos**:
- Un endpoint **rápido** para el juego en vivo (latencia < 2 s por turno).
- Un endpoint **grande** para tareas creativas (worldbuilding, generación de aventura, resúmenes profundos).

Endpoints sugeridos:

| Sirviendo | Backend recomendado | Razón |
|---|---|---|
| RTX 5090 | **vLLM** | Rendimiento estado del arte para serving en GPU NVIDIA, soporte tool-calling. |
| Mac Studio M2 Ultra | **MLX-LM** o **llama.cpp** | Aprovecha unified memory; modelos 70B Q4/Q5 caben holgadamente. |

Open WebUI puede ponerse delante como gateway si conviene.

> ⚠️ **Open WebUI / `local_openwebui`:** la `base_url` puede variar según el
> despliegue. Fase 2 debe validar el endpoint real con un check de red antes de
> asumir `/api/v1` o `/v1`. El valor actual en `config/modelos.json` es tentativo.

## Perfiles (config/perfiles.json)

```json
{
  "rapido": {
    "base_url": "http://localhost:8000/v1",
    "modelo": "Qwen/Qwen2.5-14B-Instruct",
    "max_tokens": 800,
    "temperatura": 0.7,
    "top_p": 0.9,
    "uso": "juego en vivo"
  },
  "grande": {
    "base_url": "http://mac-studio.local:8080/v1",
    "modelo": "Qwen2.5-72B-Instruct-Q5_K_M",
    "max_tokens": 4096,
    "temperatura": 0.8,
    "top_p": 0.95,
    "uso": "worldbuilding, generación de aventuras, resúmenes profundos"
  },
  "pequeno": {
    "base_url": "http://localhost:8001/v1",
    "modelo": "Qwen/Qwen2.5-3B-Instruct",
    "max_tokens": 600,
    "temperatura": 0.2,
    "uso": "parsing de intención, validaciones, tests"
  }
}
```

## Sugerencias por tarea

| Tarea | Perfil | Notas |
|---|---|---|
| Narración (escena, social, viaje) | `rapido` | Qwen 2.5 14B / Llama 3.1 8B Instruct. |
| Combate (resolución + narración corta) | `rapido` | Mismo perfil; tool-calling clave. |
| Generación de mundo / campaña / aventura | `grande` | Qwen 2.5 72B / Llama 3.3 70B en Mac. |
| Resumen de sesión profundo | `grande` | Calidad > velocidad. |
| Resumen rápido / nudges | `pequeno` | Coste mínimo. |
| Parser de intención | `pequeno` | Schema estricto. |
| Importación de aventura (extracción) | `grande` | Documentos largos. |

## Tool-calling

Verificar antes de adoptar un modelo:
- Qwen 2.5 Instruct: tool-calling OK con vLLM (`--enable-auto-tool-choice`).
- Llama 3.1/3.2/3.3 Instruct: tool-calling soportado con plantilla correcta.
- Modelos < 7B suelen fallar en tool-calling multietapa; reservados a parsing simple.

## Comprobación

Cada perfil se valida con `scripts/check_perfil.py <perfil>` (a implementar en F9): smoke chat + tool-call dummy + medición de latencia.

## Notas sobre privacidad

Todos los perfiles deben poder ser locales. Cualquier endpoint cloud (OpenRouter, Anthropic, etc.) requiere opt-in explícito en `config/proyecto.json` (`permitir_cloud: true`).
