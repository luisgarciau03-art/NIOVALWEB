# Bugs Pendientes - Auditoria Profunda 2026-03-05

## Resumen
- Fecha: 2026-03-05
- Llamadas auditadas: 653 (todo el historial de LOGS/)
- Bugs detectados: 11 llamadas (1.7%)
- Metodo: Replay FSM actual + BugDetector rule-based

---

## BUG 1: PREGUNTA_REPETIDA (10 llamadas, MEDIO)

Bruce repite la misma pregunta 2x sin que el cliente haya respondido algo nuevo.

### Llamadas afectadas:
| BRUCE ID | Negocio | Pregunta repetida | Causa raiz |
|----------|---------|-------------------|------------|
| BRUCE2650 | Ferretodito | "¿Me podria proporcionar WhatsApp o correo?" | STT garbled ("está ofreciendo es como un voto") -> UNKNOWN -> repite template |
| BRUCE2640 | Ferre Jorma | "¿Me podria proporcionar WhatsApp o correo?" | "Digame usted, en que le puedo servir?" despues de ya pedir WhatsApp -> repite |
| BRUCE2576 | Ferretodo de Chihuahua | "¿Se encontrara el encargado?" | STT garbled ("Cintura si tenemos") -> UNKNOWN -> repite encargado |
| BRUCE2462 | Ferreteria Diaz | "¿Le gustaria catalogo por WhatsApp o correo?" | STT repetido ("buen dia la orden...neumball dice") -> repite oferta |
| BRUCE2388 | Desconocido | "¿Me podria proporcionar WhatsApp o correo?" | STT garbled -> UNKNOWN -> repite template |
| BRUCE2376 | Centro Plomero de la Laguna | "Si no puede ahora, ¿me da otro contacto?" | STT garbled ("Lamentar mal triste puedo pasar") -> repite |
| BRUCE2341 | Hebel Block Termico Trejo | "¿Me podria proporcionar WhatsApp o correo?" | STT garbled -> UNKNOWN -> repite template |
| BRUCE2016 | San Benito Ferreteria Perinort | "¿Me podria proporcionar WhatsApp o correo?" | STT garbled -> UNKNOWN -> repite template |
| BRUCE1937 | Difer Tepic | "¿Me podria dar telefono?" | STT garbled -> UNKNOWN -> repite template |
| BRUCE1816 | Ferreteria Queba | "¿Me podria proporcionar WhatsApp o correo?" | STT garbled -> UNKNOWN -> repite template |

### Causa raiz comun:
- 8/10 casos: **STT entrega texto garbled/incoherente** -> classify_intent() retorna UNKNOWN
- FSM en estado capturando_contacto/encargado_ausente con UNKNOWN -> FIX 791 asigna template stateful
- El template stateful es el MISMO que ya se dijo -> PREGUNTA_REPETIDA

### Solucion propuesta (FIX 906):
- En FIX 791 (UNKNOWN->template stateful): verificar si el template ya se dijo antes
- Si ya se dijo: escalar (pedir por otro canal, ofrecer contacto Bruce, o "Disculpe, no le escuche bien")
- Similar a FIX 895 pero para el path de UNKNOWN en vez de WHAT_OFFER

---

## BUG 2: INTERRUPCION_CONVERSACIONAL (1 llamada, ALTO)

### Llamada afectada:
| BRUCE ID | Negocio | Detalle |
|----------|---------|---------|
| BRUCE2457 | Yo Mas Ferreteria | Cliente explicando algo largo ("Pero yo le yo le he visto No, es que el yo no me l...") pero Bruce interrumpio con template de pedir WhatsApp |

### Causa raiz:
- STT entrega texto parcial del cliente (cortado a mitad de explicacion)
- FSM clasifica el texto parcial y responde con template
- En produccion real, el audio del cliente aun no habia terminado

### Solucion propuesta:
- Este bug es intrinseco al timing de STT parciales en produccion
- No se puede reproducir perfectamente en replay (el replay no tiene timing real)
- Mitigation: ya existe en produccion (detector de interrupciones)

---

## Estadisticas de bugs CORREGIDOS (ya no aparecen en replay):
- GPT_LOGICA_ROTA: 70 llamadas corregidas
- CLIENTE_HABLA_ULTIMO: 38 corregidas
- SALUDO_FALTANTE: 27 corregidas
- CATALOGO_REPETIDO: 18 corregidas
- LOOP: 11 corregidas
- GPT_OPORTUNIDAD_PERDIDA: 8 corregidas
- GPT_RESPUESTA_INCOHERENTE: 5 corregidas
- GPT_CONTEXTO_IGNORADO: 5 corregidas
- DICTADO_INTERRUMPIDO: 3 corregidas
- TRANSFER_IGNORADA: 2 corregidas
