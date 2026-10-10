# Perfil España (borrador `es/loreg/v0.1`)

[English](profile-es.md) · **Español**

Traducción informativa. Si difiere de la [versión inglesa](profile-es.md),
manda la inglesa.

Estado: **borrador, todavía sin validar con ficheros reales** (véase el
apartado 5).

Este perfil traduce los resultados de las elecciones generales españolas al
formato del núcleo. La norma aplicable es la Ley Orgánica 5/1985 del Régimen
Electoral General (LOREG).

## 1. Alcance

- Admitidas: elecciones al Congreso de los Diputados (tipo de elección `02`
  del Ministerio), donde la circunscripción es la provincia. Ceuta y Melilla
  tienen su propio código de provincia.
- Aún no admitidas: Senado, municipales, europeas y autonómicas. Las
  autonómicas tienen leyes y modelos de acta propios.

## 2. Identificadores

| Campo del núcleo | Forma | Ejemplo |
| --- | --- | --- |
| `election` | `es/congreso/<aaaa>-<mm>` | `es/congreso/2019-11` |
| `constituency` | `es/<provincia>` | `es/08` |
| `station` | `es/<provincia>/<municipio>/<distrito>/<sección>/<mesa>` | `es/08/019/01/001/A` |

Los códigos son los de los ficheros del Ministerio: provincia (2 dígitos),
municipio (3), distrito (2), sección (hasta 4 caracteres, sin espacios
alrededor) y letra de mesa (1).

Los códigos de candidatura son los de 6 dígitos de los ficheros del
Ministerio para esa elección. No son estables de una elección a otra.

## 3. Fuente de los datos oficiales

El Ministerio del Interior publica ficheros ZIP por elección en
<https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/>.
Cada ZIP contiene ficheros de texto de ancho fijo, codificados en ISO-8859-1
y con nombre `NNTTAAMM.DAT`.

| ZIP | Fichero | Contenido | Uso |
| --- | --- | --- | --- |
| `…_MESA.zip` | `09` | Una fila por mesa | Cabecera y totales de la declaración |
| `…_MESA.zip` | `10` | Una fila por mesa y candidatura | `counts.candidatures` |
| `…_TOTA.zip` | `07` | Una fila por provincia o ámbito superior | Totales oficiales |
| `…_TOTA.zip` | `08` | Una fila por provincia (o superior) y candidatura | Totales oficiales por candidatura |

Columnas leídas (desde 1, ambas incluidas):

| Fichero | Campo | Columnas |
| --- | --- | --- |
| todos | tipo de elección, año, mes | 1–2, 3–6, 7–8 |
| todos | provincia | 12–13 |
| 09, 10 | municipio, distrito, sección, mesa | 14–16, 17–18, 19–22, 23 |
| 09 | electores censados (censo INE) | 24–30 |
| 09 | votos en blanco, nulos, a candidaturas | 66–72, 73–79, 80–86 |
| 09 | indicador de datos oficiales | 101 |
| 10 | código de candidatura, votos | 24–29, 30–36 |
| 07 | número de mesas | 73–77 |
| 07 | votos en blanco, nulos, a candidaturas | 126–133, 134–141, 142–149 |
| 08 | código de candidatura, votos | 15–20, 21–28 |

Las filas con código de provincia `99` son subtotales y se ignoran: totales
nacionales y autonómicos en los ficheros `07` y `08`, y totales del voto
exterior (CERA) por comunidad autónoma en los ficheros `09` y `10`. El voto
exterior aparece además como una fila por provincia, con código de municipio
`999`. Esas filas se conservan con `unit` igual a `aggregate`: suman votos a
la provincia, pero el número de mesas del Ministerio no las incluye.

En los ficheros de noviembre de 2019 el ZIP `_MESA` contiene también los
ficheros `07` y `08` y una copia del documento de diseño de registro del
Ministerio (`FICHEROS.doc`).

Estas posiciones se han tomado del diseño de registro tal como lo implementa
el paquete de R [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
de rOpenSpain (Meleiro, 2024), no del documento de diseño del propio
Ministerio.

## 4. Correspondencia con el acta

El artículo 97.2 de la LOREG enumera lo que recoge el acta de escrutinio de
la mesa: electores censados, certificaciones censales aportadas, votantes,
papeletas nulas, votos en blanco y votos obtenidos por cada candidatura.

| Acta (art. 97.2) | Campo de la declaración | ¿Está en los ficheros del Ministerio? |
| --- | --- | --- |
| Electores censados | `counts.registered` | Sí (fichero 09) |
| Certificaciones censales aportadas | — | No encontrado |
| Votantes | derivado: blancos + nulos + votos a candidaturas | No como cifra final separada |
| Papeletas nulas | `counts.null` | Sí |
| Votos en blanco | `counts.blank` | Sí |
| Votos por candidatura | `counts.candidatures` | Sí (fichero 10) |

Las cifras de voto exterior del fichero 09 (`censo_cera`, `censo_cere`,
`votantes_cere`) se conservan en `extra` y no intervienen en la verificación.

## 5. Lagunas conocidas y supuestos sin verificar

1. **Aún no hay una ejecución completa con datos reales.** Un primer intento
   con los ficheros de noviembre de 2019 reveló las filas de provincia 99
   descritas en el apartado 3. Por lo demás, el lector se ha probado con
   ficheros sintéticos y con dos filas reales.
2. Los artículos de la LOREG se han leído en una transcripción no oficial, no
   en el BOE. No se ha revisado una modificación publicada el 2 de julio de
   2026.
3. Se supone que los códigos de candidatura del fichero 10 y del fichero 08
   son el mismo conjunto. Si el Ministerio agrupa candidaturas con códigos
   distintos a nivel provincial, la comparación necesita la correspondencia
   del fichero `03`.
4. El voto exterior (CERA) aparece como una fila por provincia, similar a una
   mesa (municipio `999`). Se ha visto en los ficheros de noviembre de 2019;
   falta confirmar que con esas filas la suma de mesas alcanza el total
   provincial.
5. No se sabe si los ficheros por mesa contienen resultados provisionales o
   definitivos, ni cómo tratan las correcciones del escrutinio general
   (arts. 103 a 108 de la LOREG). Por tanto, una diferencia puede ser
   legítima.
6. Una declaración construida a partir de estos ficheros es evidencia sobre
   el **conjunto de datos publicado**, no sobre el acta en papel. Que los
   totales cuadren demuestra que las dos publicaciones del Ministerio son
   coherentes entre sí.
