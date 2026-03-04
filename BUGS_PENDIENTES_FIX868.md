# Bugs Pendientes - Post FIX 868
> Replay masivo 450 llamadas (máx dataset) | 2026-03-03
> Pre-FIX 868: 335 bugs originales → 24 nuevos (92.8% reducción)
> Post-FIX 868: 335 bugs originales → 13 nuevos (96.1% reducción)
> FIX 868 eliminó 11 de 24 bugs (46% de los nuevos)

## Resumen Final

| Métrica | Pre-868 | Post-868 |
|---|---|---|
| Llamadas | 450 | 450 |
| Bugs originales | 335 | 335 |
| Bugs corregidos | 303 | 303 |
| Bugs en replay | 24 | 13 |
| Reducción total | 92.8% | 96.1% |

## FIX 868 - Correcciones Aplicadas

| FIX | Descripción | Bugs eliminados |
|---|---|---|
| 868A | Variantes encargado ausente (salió, se fue, no ha llegado) | BRUCE2271, 2130, 2041 |
| 868B | Variantes área equivocada (taller mecánico, somos tienda de) | BRUCE1893, 2016, 1730, 2474 |
| 868C | Exemption callback-question en INTERRUPCION | BRUCE2130 |
| 868D | _CONFIRMACION_DATO_862 extendido (pedir contacto=no oferta) | BRUCE2214 |
| 868E | Esperando transferencia exemption CLIENTE_HABLA_ULTIMO | BRUCE1817 |
| 868F | Smart dedup PREGUNTA_REPETIDA (STT artifact) | BRUCE1885, 1895 |
| 868G | Normalización puntuación para no_esta check | BRUCE2474 |
| 868H | Skip INTERRUPCION cuando señal no-negocio detectada | BRUCE2016, 1730 |

## 13 Bugs Restantes (legítimos)

### INTERRUPCION_CONVERSACIONAL (3x)
| BRUCE ID | Negocio | Nota |
|---|---|---|
| BRUCE2446 | TORBOLT MEXICANA S.A. DE C.V. | FSM replay artifact |
| BRUCE2096 | Ferretera De Abastos Suc Quiroga | FSM replay artifact |
| BRUCE1797 | Fix Ferreterías Uruapan II | FSM replay artifact |

### PREGUNTA_REPETIDA (4x)
| BRUCE ID | Negocio |
|---|---|
| BRUCE2529 | City Tools Ferreterías |
| BRUCE2477 | PRIVAL Plomeria |
| BRUCE2344 | MATERIALES HERRERA |
| BRUCE1975 | FERREVARIOS |

### AREA_EQUIVOCADA (2x)
| BRUCE ID | Negocio |
|---|---|
| BRUCE2491 | Grupo Ferretero Angeles Loma |
| BRUCE1897 | Ferretería y Herrajes La Nueva |

### Otros (4x)
| BRUCE ID | Negocio | Bug |
|---|---|---|
| BRUCE1975 | FERREVARIOS | LOOP + TRANSFER_IGNORADA |
| BRUCE2038 | San Benito Ferretería Perinorte | PITCH_REPETIDO |
| BRUCE1914 | Insupromex S.A de C.V | PREGUNTA_IGNORADA |

## Nota
Los 13 bugs restantes son comportamientos legítimos del FSM en modo replay
(templates vs GPT real) o bugs genuinos que requieren cambios en agente_ventas.py,
no en el bug_detector.
