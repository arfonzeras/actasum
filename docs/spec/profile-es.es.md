# Perfil España (borrador `es/loreg/v0.1`)

[English](profile-es.md) · **Español**

Traducción informativa. Si difiere de la [versión inglesa](profile-es.md),
manda la inglesa.

Estado: **borrador, ejecutado con cinco elecciones al Congreso** (de 2008 a
2023; véanse el apartado 5 y
[`../findings/es-congreso.md`](../findings/es-congreso.md)).

Este perfil traduce los resultados de las elecciones generales españolas al
formato del núcleo. La norma aplicable es la Ley Orgánica 5/1985 del Régimen
Electoral General (LOREG).

## 1. Alcance

- Admitidas y ejecutadas con ficheros reales: elecciones al Congreso de los
  Diputados (tipo de elección `02` del Ministerio), donde la circunscripción
  es la provincia. Ceuta y Melilla tienen su propio código de provincia.
- Admitidas y ejecutadas con dos ficheros reales cada una: municipales (tipo
  `04`), donde la circunscripción es el municipio, y europeas (tipo `07`),
  donde la circunscripción es todo el país. Véanse la sección 3.3 del texto
  en inglés y [`../findings/es-other-elections.md`](../findings/es-other-elections.md).
- No admitidas: Senado (se vota a candidatos, no a candidaturas),
  autonómicas (leyes y modelos de acta propios), cabildos y referéndums.

## 2. Identificadores

| Campo del núcleo | Forma | Ejemplo |
| --- | --- | --- |
| `election` | `es/<tipo>/<aaaa>-<mm>`, con tipo `congreso`, `municipales` o `europeas` | `es/congreso/2019-11` |
| `constituency` (Congreso) | `es/<provincia>` | `es/08` |
| `constituency` (municipales) | `es/<provincia>/<municipio>` | `es/08/019` |
| `constituency` (europeas) | `es` | `es` |
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
| `…_MESA.zip` | `05` | Una fila por municipio y por distrito municipal | Totales oficiales por municipio |
| `…_MESA.zip` | `06` | Una fila por municipio (o distrito) y candidatura | Totales oficiales por candidatura y municipio |
| `…_TOTA.zip` | `07` | Una fila por provincia o ámbito superior | Totales oficiales |
| `…_TOTA.zip` | `08` | Una fila por provincia (o superior) y candidatura | Totales oficiales por candidatura |

Columnas leídas (desde 1, ambas incluidas):

| Fichero | Campo | Columnas |
| --- | --- | --- |
| todos | tipo de elección, año, mes | 1–2, 3–6, 7–8 |
| todos | provincia | 12–13 |
| 09, 10 | municipio, distrito, sección, mesa | 14–16, 17–18, 19–22, 23 |
| 09 | electores censados (censo de escrutinio, o censo CERA en las filas de voto exterior) | 31–37 |
| 09 | censo del INE (se guarda en `extra` cuando difiere) | 24–30 |
| 09 | votos en blanco, nulos, a candidaturas | 66–72, 73–79, 80–86 |
| 09 | indicador de datos oficiales | 101 |
| 10 | código de candidatura, votos | 24–29, 30–36 |
| 07 | número de mesas | 73–77 |
| 07 | votos en blanco, nulos, a candidaturas | 126–133, 134–141, 142–149 |
| 08 | código de candidatura, votos | 15–20, 21–28 |
| 05 | municipio, distrito (`99` = total municipal) | 14–16, 17–18 |
| 05 | número de mesas | 137–141 |
| 05 | votos en blanco, nulos, a candidaturas | 190–197, 198–205, 206–213 |
| 06 | provincia, municipio, distrito | 10–11, 12–14, 15–16 |
| 06 | código de candidatura, votos | 17–22, 23–30 |

Las filas con código de provincia `99` son subtotales y se ignoran: totales
nacionales y autonómicos en los ficheros `07` y `08`, y totales del voto
exterior (CERA) por comunidad autónoma en los ficheros `09` y `10`. El voto
exterior aparece además como una fila por provincia, con código de municipio
`999`. Esas filas se conservan con `unit` igual a `aggregate`: suman votos a
la provincia, pero el número de mesas del Ministerio no las incluye.

El ZIP `_MESA` contiene también los ficheros `07` y `08`, de modo que basta
por sí solo, y una copia del documento de diseño de registro del Ministerio
(`FICHEROS.doc`).

Estas posiciones se tomaron primero del paquete de R
[`infoelectoral`](https://github.com/rOpenSpain/infoelectoral) de rOpenSpain
(Meleiro, 2024) y después se contrastaron con el documento de diseño de
registro del propio Ministerio, *Ficheros de Carga de Datos de Elecciones*
(2010), que viene dentro de los ZIP como `FICHEROS.doc`. Todas las posiciones
de la tabla anterior coinciden con ese documento.

### 3.1 Nivel municipal

La circunscripción es la provincia, pero el mismo ZIP publica totales por
municipio. El lector puede comparar también a ese nivel
(`grouping: station-prefix/3`, áreas como `es/45/168`), lo que muestra en qué
municipios nace una diferencia provincial. Solo se usan las filas del total
municipal (distrito `99`). Las filas de voto exterior no pertenecen a ningún
municipio y quedan fuera de esta comparación.

### 3.2 Residuo del voto exterior

Los ficheros no traen un total oficial del voto exterior por provincia. El
total provincial menos la suma de sus municipios es lo que las cifras
oficiales dejan para el voto exterior. `--level overseas` compara ese residuo
con la fila de voto exterior del fichero por mesa. Junto con el nivel
municipal, indica si una diferencia provincial está en las mesas o en la fila
de voto exterior.

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

Otras cifras del fichero 09 (`censo_ine`, y las de residentes extranjeros
`censo_cere` y `votantes_cere`) se conservan en `extra` y no intervienen en
la verificación.

## 5. Lagunas conocidas y supuestos sin verificar

1. **Cinco ejecuciones reales hasta ahora**, todas de elecciones al Congreso
   entre 2008 y 2023. El diseño se mantuvo en todas. No se han probado
   elecciones más antiguas ni otros tipos de elección.
2. Los artículos 79 y 95 a 108 de la LOREG se comprobaron el 11 de octubre
   de 2026 en el texto consolidado del BOE (referencia BOE-A-1985-11672,
   última modificación de 2 de julio de 2026). Los artículos 108, 163, 173,
   180, 191, 214, 216 y 224 se leyeron el 31 de octubre de 2026 en el mismo
   texto. El resto de la ley no se ha leído para este perfil. Estos artículos
   se aplican a elecciones de 2008 a 2024 en su redacción de 2026; no se ha
   comparado con la redacción vigente el día de cada elección. La modificación de julio de 2026 (Ley Orgánica
   2/2026) cambia los artículos 161.2 y 165.2, sobre las circunscripciones
   del Senado, y no afecta al escrutinio.
3. Los códigos de candidatura del fichero 10 y del fichero 08 son el mismo
   conjunto en los ficheros de noviembre de 2019, puesto que cuadran todos
   los totales por candidatura. No está confirmado para otras elecciones; si
   falla, la correspondencia está en el fichero `03`.
4. El voto exterior (CERA) aparece como una fila por provincia, similar a una
   mesa (municipio `999`). En los ficheros de noviembre de 2019, las filas de
   mesa más estas filas suman exactamente los totales provinciales.
5. No se sabe si los ficheros por mesa contienen resultados provisionales o
   definitivos, ni cómo tratan las correcciones del escrutinio general
   (arts. 103 a 108 de la LOREG). Por tanto, una diferencia puede ser
   legítima.
6. Una declaración construida a partir de estos ficheros es evidencia sobre
   el **conjunto de datos publicado**, no sobre el acta en papel. Que los
   totales cuadren demuestra que las dos publicaciones del Ministerio son
   coherentes entre sí.

## 6. Ficha de verificabilidad

`actasum es context --mesa MESA.zip` escribe un borrador del contexto de la
ficha (docs/spec/verifiability.md, en inglés) a partir de los ficheros del
Ministerio: escaños por provincia en el Congreso (fichero 08, columnas
29-33, con los nombres del fichero 07), concejales por municipio en las
municipales (fichero 05, columnas 214-216; los municipios solo como
distribución, nunca en un listado), los escaños de las europeas en la fila
nacional del fichero 08 (54 en mayo de 2019 y 61 en junio de 2024, los del
artículo 2 de cada real decreto de convocatoria) sin barrera, porque el
artículo 216 aplica el 163 salvo su apartado 1.a, la fila del CERA de cada
provincia como canal de voto exterior y el voto por correo como no publicado
aparte. En 2019 la ficha calcula solo los 54 escaños del artículo 2; los
cinco que la Junta Electoral Central asignó tras la salida del Reino Unido
quedan fuera, porque no se ha leído cómo se asignaron. Los detalles están en
la versión inglesa, sección 6.

### 6.1 Qué cuenta como proclamado

Leído en el texto consolidado de la LOREG (BOE-A-1985-11672, última
modificación de 2 de julio de 2026):

- **Congreso y municipales.** Las juntas competentes proclaman a los electos
  al día siguiente de terminar el plazo de reclamaciones sin que las haya, o
  de resolverlas la Junta Electoral Central (artículo 108.4). Son las juntas
  provinciales en el Congreso (artículo 173) y las de zona en las municipales
  (artículo 191.1). La proclamación consta en un acta de proclamación con
  electores, votantes, votos de cada candidatura, en blanco, válidos y nulos,
  escaños de cada candidatura y relación de electos (artículo 108.5). La
  Junta Electoral Central publica en el BOE los resultados generales y por
  circunscripciones en cuarenta días, «sin perjuicio de los recursos
  contencioso-electorales contra la proclamación de electos» (artículo 108.6).
- **Parlamento Europeo.** La Junta Electoral Central hace el recuento
  nacional, atribuye los escaños y proclama a los electos no más tarde del
  vigésimo día posterior a las elecciones (artículo 224.1).
- **Para publicar una ficha**, una elección cuenta como proclamada cuando lo
  está cada circunscripción de su ficha: las 52 provincias en el Congreso, el
  país en las europeas y cada municipio de la ficha en las municipales. La
  prueba pública que un lector puede comprobar es la publicación en el BOE
  del artículo 108.6; no consta que se publiquen las actas de proclamación de
  las juntas. Queda sin decidir si un recurso contencioso-electoral contra
  la proclamación (artículos 109 y 112.1, en tres días) debe retrasar la
  publicación.
