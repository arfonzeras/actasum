# actasum

[English](https://github.com/arfonzeras/actasum/blob/main/README.md) · **Español**

*Antes `tallylog`; renombrado el 11 de octubre de 2026.*

Un formato abierto y un verificador para las actas de escrutinio de las mesas
electorales.

Tras una elección, cada mesa anota su resultado en un acta. Después, la
autoridad electoral suma esas actas. `actasum` permite que cualquiera repita
esa suma a partir de las cifras de cada mesa y la compare con los totales
publicados.

No se ocupa de la votación, de la identidad del votante ni de las papeletas.
Se ocupa del tramo que va de la mesa al resultado publicado.

> **Estado: borrador inicial (v0.1).** El formato va a cambiar. El
> verificador se ha ejecutado con ficheros publicados de España, Colombia,
> México y Brasil (véase más abajo). No te fíes todavía de su salida para
> nada más.

Esta página es una traducción informativa. Si difiere del
[README en inglés](https://github.com/arfonzeras/actasum/blob/main/README.md), manda la versión inglesa.

## Elecciones ejecutadas

Cada ejecución compara entre sí publicaciones de una misma autoridad
electoral: sus ficheros por mesa con sus propios totales. Que **cuadren**
significa que esas publicaciones son coherentes: los totales publicados son
la suma de las cifras por mesa publicadas. No es una verificación. Ninguna
ejecución ha comparado los ficheros con las actas en papel, y una diferencia
no dice qué cifra es la correcta ni por qué.

Por eso todas figuran como **ejecutado, no verificado**.

| País | Elección | Mesas | Qué cuadra | Qué no | Estado | Hallazgos |
| --- | --- | --- | --- | --- | --- | --- |
| España | Congreso, marzo de 2008 | 59.346 | 50 de 52 circunscripciones; 8.111 de 8.112 municipios | Filas del voto exterior de Barcelona y Murcia; un municipio de Soria | ejecutado, no verificado | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| España | Congreso, junio de 2016 | 57.531 | 52 de 52 circunscripciones | — | ejecutado, no verificado | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| España | Congreso, abril de 2019 | 60.038 | 52 de 52 circunscripciones | — | ejecutado, no verificado | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| España | Congreso, noviembre de 2019 | 59.555 | 52 de 52 circunscripciones; 8.131 de 8.131 municipios | — | ejecutado, no verificado | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| España | Congreso, julio de 2023 | 60.314 | 50 de 52 circunscripciones; 8.131 de 8.131 municipios | Filas del voto exterior de Cantabria y Toledo | ejecutado, no verificado | [es-congreso](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) |
| España | Parlamento Europeo, junio de 2024 | 58.556, más 52 filas del voto exterior | El país y las 52 provincias | — | ejecutado, no verificado | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| España | Parlamento Europeo, mayo de 2019 | 60.076, más 52 filas del voto exterior | 38 de 52 provincias; 8.126 de 8.131 municipios | El país: los tres niveles publicados no suman entre sí | ejecutado, no verificado | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| España | Municipales, mayo de 2023 | 57.681 | 5.248 de 5.272 municipios | 24 municipios; en 5, los votos por mesa darían otros concejales | ejecutado, no verificado | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| España | Municipales, mayo de 2019 | 57.188 | 5.270 de 5.291 municipios | 21 municipios; 8 repartos de concejales por explicar | ejecutado, no verificado | [es-other-elections](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) |
| Colombia | Presidente, 31 de mayo de 2026, Bogotá D.C. | 17.157 | Las 16 cifras de votos del resultado oficial (E-26); las 6.410 modificaciones del acta general concuerdan con el fichero | Mesas: 17.164 en el E-24. El fichero publicado es el de la comisión desplazado 13 bytes; reparado y comprobado con la huella del acta general | ejecutado, no verificado | [co-presidente-2026](https://github.com/arfonzeras/actasum/blob/main/docs/findings/co-presidente-2026.md) |
| Colombia | Presidente, 31 de mayo de 2026, Córdoba | 4.176 | Las 16 cifras de votos del E-26 | — (el registro de modificaciones es un escaneado y no se leyó) | ejecutado, no verificado | [co-presidente-2026](https://github.com/arfonzeras/actasum/blob/main/docs/findings/co-presidente-2026.md) |
| México | Presidencia, 2 de junio de 2024 | 158.972 en la captura, 170.621 en el cómputo | Las declaraciones del cómputo dan cada cifra de un comunicado del INE | Ninguna suma lo iguala: la captura tiene cifras sin leer y queda al menos 1.883 por encima en candidaturas no registradas; la suma de lo que queda en pie incluye 5.265 votos de 16 mesas cuyo paquete no se recibió | ejecutado, no verificado | [mx-presidencia-2024](https://github.com/arfonzeras/actasum/blob/main/docs/findings/mx-presidencia-2024.md) |
| Brasil | Presidente, 4 de octubre de 2026, primera vuelta | 499.206 | Todas las cifras de votos de los 28 informes de los estados y el exterior, y del nacional | Una sección del exterior no tiene fila en el fichero (su informe da 0 votantes) | ejecutado, no verificado | [br-presidente-2026](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026.md) |
| Brasil | Presidente, 25 de octubre de 2026, segunda vuelta | 499.205 | Todas las cifras de votos de los 28 informes de los estados y el exterior, y del nacional | Dos secciones del exterior no tienen fila de presidente en el fichero (su informe da 0 votantes) | ejecutado, no verificado | [br-presidente-2026-2t](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-2t.md) |

En Brasil, 5.246 votos del número 28 se comparan como nulos porque los
informes oficiales declaran que los cuentan así; el verificador lo dice en
su resultado. En la segunda vuelta no se cuenta ningún voto como otra
partida. Los informes brasileños dicen que su resultado puede cambiar.

Los hallazgos están en inglés.

### Cómo reproducir cada ejecución

Este repositorio no incluye datos electorales. Cada ejecución parte de
ficheros descargados de la autoridad; la huella es la del fichero tal como se
descargó.

**España.** Los ZIP por mesa `02AAAAMM_MESA.zip` (Congreso),
`07AAAAMM_MESA.zip` (Parlamento Europeo) y `04AAAAMM_MESA.zip`
(municipales), del
[área de descargas](https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/)
del Ministerio del Interior.

```sh
actasum es replay --mesa 02201911_MESA.zip                       # per constituency
actasum es replay --mesa 02202307_MESA.zip --level municipality  # per municipality
actasum es replay --mesa 07202406_MESA.zip --level province      # per province
actasum es seats  --mesa 04202305_MESA.zip                       # would a difference change a seat?
```

| Fichero | SHA-256 |
| --- | --- |
| `02201911_MESA.zip` | `e7b621f295d7bf79b794941d4f11e7bcf7bd971ecbd6eb21dd4269d59926e441` |
| `07202406_MESA.zip` | `ed30e4cf11772afb0785f2992f44fa191b8671f933865335b7093ac9ccb6659b` |
| `07201905_MESA.zip` | `8199711babd4b61ee4940469351ab4a263b0cf84a84ccfbe04ab1970a4c1a474` |
| `04202305_MESA.zip` | `20dac696cd2efaa63c9346384ddb682f3da4fda92c6af67447159a60f1ab0de3` |
| `04201905_MESA.zip` | `b8b1c649e3841ba735383152fd3a38259a336698d1eb79f7a653cae54c02e204` |
| `02200803_MESA.zip` | `9dd65b74aae646cc6f5e9dfbaaa6520f029b6f3cbac76f2c369d7b96e7d8081d` |
| `02201606_MESA.zip` | `d41c21244a5810fe596bac18352fd9820ab197662ee744de87b7db08e507a5ce` |
| `02201904_MESA.zip` | `92f2ff6c1c9a6504d6d3647fa365c64a3502d36e15440364aa94f478e7d40764` |
| `02202307_MESA.zip` | `e78fc231326a03cf67bbec87b7100ea0c8c46859daa1b2a631c06daaaf1717f8` |

Las cuatro últimas huellas se anotaron el 31 de octubre de 2026, de copias
cuya ejecución da las mismas cifras que los hallazgos; de los ficheros de las
primeras ejecuciones no se tomó la huella.

**Colombia.** El fichero por mesa (`MMV_…csv`) y el acta general de
escrutinio de la comisión escrutadora general de cada departamento, del
[sitio de escrutinios](https://escrutiniospresidente2026.registraduria.gov.co/published)
de la Registraduría. Los totales oficiales se teclearon del E-26 escaneado y
están en [`docs/findings/official/`](https://github.com/arfonzeras/actasum/tree/main/docs/findings/official/).

```sh
# Bogotá: the AGE's text gives the changes and the hash of the original file
pdftotext -layout AGE.pdf AGE.txt
actasum co convert --mmv MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv --election 2026-05 \
    --age-text AGE.txt --out statements.jsonl
actasum verify --statements statements.jsonl \
    --official docs/findings/official/co-presidente-2026-05-bogota.official.json

# Córdoba
actasum co convert --mmv MMV_XXX_13_000_XXX_XX_XX_XXX_1007.csv --election 2026-05 \
    --sha256 2799c27a52574d85753ee0d31475cebdafd7819f88f1d977fe3b718fc6d636c9 \
    --out statements.jsonl
actasum verify --statements statements.jsonl \
    --official docs/findings/official/co-presidente-2026-05-cordoba.official.json
```

| Fichero | SHA-256 |
| --- | --- |
| Bogotá, `MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv` tal como se descargó | `6cec1c68ac67c73407fb1cfd30a337bab08b8b850e6d679c918d98f5e4ec000e` |
| Bogotá, el mismo fichero tal como lo generó la comisión, según el acta general | `dfa5612022c2763666cd72d9553bbcfd5cfcab60076fc4a95889503a34a6ce25` |
| Córdoba, `MMV_XXX_13_000_XXX_XX_XX_XXX_1007.csv` | `2799c27a52574d85753ee0d31475cebdafd7819f88f1d977fe3b718fc6d636c9` |

**México.** Las bases de datos del PREP y de los Cómputos Distritales del
INE para la elección presidencial. No se anotó la dirección de la que se
descargaron. Los totales oficiales se teclearon del comunicado de prensa 368
del INE.

```sh
# PRES_2024.csv inside 20240603_2005_PREP.zip › 20240603_2005_PREP_PRES.zip, and
# inside 20240608_2030_COMPUTOS.zip › 20240608_2030_COMPUTOS_PRES.zip
actasum mx replay --prep PREP/PRES_2024.csv --computos COMPUTOS/PRES_2024.csv \
    --election 2024-06 --official docs/findings/official/mx-presidencia-2024-06.official.json
```

| Fichero | SHA-256 |
| --- | --- |
| `20240603_2005_PREP.zip` | `dcccf23088f81a4ab7c7942a79504b04c4a9347b0a4744f6c328c59fd4d6c31d` |
| su `PRES_2024.csv` | `c9d7282e9ba0dabdc6d0378eb3383010ad3f301a26d79c3035a9f2a2fd6d5c45` |
| `20240608_2030_COMPUTOS.zip` | `f0b0f90483720374eaac50cfb356b43425697fabfa3f963d22a5b8f2d849312f` |
| su `PRES_2024.csv` | `860c1a539ac98b5def4dff3e82e87a19be3ebba7cb435b680ae79799942d1628` |

**Brasil.** Los 28 ficheros de boletines de urna del TSE
`bweb_1t_<UF>_051020261403.zip` (26 estados, el Distrito Federal y `ZZ`, el
exterior), del conjunto de datos
[Resultados - 2026 - Boletim de Urna](https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna),
y los 29 informes de totalización de presidente
`Relatorio_Resultado_Totalizacao_2026_<UF>.zip` (los mismos 27 y `BR`), de
`https://cdn.tse.jus.br/estatistica/sead/odsele/relatorio_resultado_totalizacao/`.
`actasum br official` necesita `pdftotext` (Poppler).

```sh
actasum br official --round 1 \
    $(for f in Relatorio_Resultado_Totalizacao_2026_*.zip; do printf -- '--report %s ' "$f"; done) \
    --states-out states.official.json --country-out brasil.official.json
actasum br replay \
    $(for f in bweb_1t_*_051020261403.zip; do printf -- '--bu %s ' "$f"; done) \
    --official docs/findings/official/br-presidente-2026-10-04-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-04-brasil.official.json
```

El TSE publica una SHA-512 junto a cada fichero de boletines; las 28 están en
[`docs/findings/br-presidente-2026-1t.sha512`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-1t.sha512)
(`shasum -a 512 -c` las comprueba). La SHA-256 de cada informe, y su hora de
emisión, están en los dos ficheros de totales oficiales citados arriba. Los
ZIP de los informes traen ahora también los de la segunda vuelta, y cuatro
informes de la primera (MG, RN, RO, RS) se emitieron de nuevo con las mismas
cifras: escritos con los ficheros publicados ahora, los totales oficiales de
la primera vuelta tienen las mismas cifras y el mismo `count_as`, y otras
huellas y horas de emisión.

La segunda vuelta: los 28 ficheros `bweb_2t_<UF>_261020260742.zip` del mismo
conjunto de datos (en el portal, los lista la página en inglés) y los mismos
29 ZIP de informes.

```sh
actasum br official --round 2 \
    $(for f in Relatorio_Resultado_Totalizacao_2026_*.zip; do printf -- '--report %s ' "$f"; done) \
    --states-out states.official.json --country-out brasil.official.json
actasum br replay \
    $(for f in bweb_2t_*_261020260742.zip; do printf -- '--bu %s ' "$f"; done) \
    --official docs/findings/official/br-presidente-2026-10-25-states.official.json \
    --official docs/findings/official/br-presidente-2026-10-25-brasil.official.json
```

Sus SHA-512 están en
[`docs/findings/br-presidente-2026-2t.sha512`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-2t.sha512).

## Qué hay aquí

| Ruta | Contenido |
| --- | --- |
| [`docs/spec/core.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/core.md) | Formato y procedimiento de verificación, independientes del país (en inglés) |
| [`docs/spec/log.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/log.md) | Registro de solo añadir: puntos de control y pruebas de inclusión y de consistencia (en inglés) |
| [`docs/spec/witness.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/witness.md) | Puntos de control firmados y testigos que los cofirman (en inglés) |
| [`docs/spec/profile-es.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-es.md) | Perfil España: identificadores, fuente de datos, lagunas conocidas ([traducción](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-es.es.md)) |
| [`docs/findings/es-congreso.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-congreso.md) | España, elecciones al Congreso (en inglés) |
| [`docs/findings/es-other-elections.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md) | España, dos europeas y dos municipales (en inglés) |
| [`docs/spec/profile-co.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-co.md) | Perfil Colombia (borrador; en inglés) |
| [`docs/findings/co-presidente-2026.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/co-presidente-2026.md) | Colombia, presidencial de mayo de 2026: Bogotá y Córdoba comparadas con la huella y los totales de sus propias comisiones (en inglés) |
| [`docs/spec/profile-mx.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-mx.md) | Perfil México (borrador): bases de datos del PREP y de los Cómputos Distritales del INE (en inglés) |
| [`docs/findings/mx-presidencia-2024.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/mx-presidencia-2024.md) | México, presidencial de junio de 2024: la captura y el cómputo, mesa por mesa (en inglés) |
| [`docs/spec/profile-br.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/profile-br.md) | Perfil Brasil (borrador): ficheros de boletines de urna del TSE (en inglés) |
| [`docs/findings/br-presidente-2026.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026.md) | Brasil, presidencial de octubre de 2026, primera vuelta: todos los estados y el exterior frente a los informes de totalización del TSE (en inglés) |
| [`docs/findings/br-presidente-2026-2t.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/br-presidente-2026-2t.md) | Lo mismo, segunda vuelta (en inglés) |
| [`docs/releasing.md`](https://github.com/arfonzeras/actasum/blob/main/docs/releasing.md) | Cómo se publica una versión en PyPI (en inglés) |
| [`schemas/statement.schema.json`](https://github.com/arfonzeras/actasum/blob/main/schemas/statement.schema.json) | Esquema JSON de una declaración de acta |
| `src/actasum/` | Implementación de referencia en Python; solo biblioteca estándar, salvo para las firmas |
| `tests/` | Pruebas con datos sintéticos |

## Inicio rápido

Requiere Python 3.10 o posterior. Sin dependencias, salvo `cryptography`
para las firmas y los testigos.

```sh
pip install -e .
```

Descarga el ZIP de mesas (`_MESA`) de una elección al Congreso desde el
[área de descargas](https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/)
del Ministerio del Interior y ejecuta:

```sh
actasum es replay --mesa 02201911_MESA.zip
```

Ese ZIP contiene tanto los ficheros por mesa como los totales provinciales.
Con `--tota` se pueden leer los totales de otro fichero.

Para ver en qué municipios nace una diferencia, compara un nivel más abajo:

```sh
actasum es replay --mesa 02202307_MESA.zip --level municipality
```

También se leen las municipales (`04…_MESA.zip`) y las europeas
(`07…_MESA.zip`), con el municipio y el país entero como circunscripción. De
momento se han ejecutado dos elecciones de cada tipo; véase
[`docs/findings/es-other-elections.md`](https://github.com/arfonzeras/actasum/blob/main/docs/findings/es-other-elections.md)
(en inglés). Para un primer vistazo a un ZIP:

```sh
actasum es describe --mesa 07202406_MESA.zip
```

Una mesa puede tener varias declaraciones: varias capturas de la misma acta,
que deben coincidir, y actos posteriores como una corrección en el
escrutinio general o una votación repetida, que pueden diferir legítimamente.
El verificador muestra entonces dos sumas, lo que contaron las mesas y lo que
quedó firme, y dice con cuál coinciden los totales oficiales
([especificación del núcleo](https://github.com/arfonzeras/actasum/blob/main/docs/spec/core.md), secciones 3.3 y 5.2, en
inglés).

La orden indica cuántas circunscripciones cuadran y lista cada diferencia.
Termina con `0` si todo cuadra, con `1` si hay diferencias o lagunas, y con
`2` si no puede leer la entrada.

Lo mismo en pasos separados, generando los ficheros intermedios neutrales:

```sh
actasum es convert  --mesa 02201911_MESA.zip --out statements.jsonl
actasum es official --tota 02201911_MESA.zip --out official.json
actasum verify --statements statements.jsonl --official official.json
```

La salida del programa está en inglés.

## El registro

Las declaraciones se pueden cargar en un registro de solo añadir. Un punto de
control de tres líneas compromete todas las entradas, y unas pruebas breves
demuestran que la declaración de una mesa está en el registro, o que el
registro solo ha crecido.

```sh
actasum es convert --mesa 02201911_MESA.zip --out statements.jsonl
actasum log build --statements statements.jsonl --out log-2019-11 > checkpoint.txt

actasum log prove --log log-2019-11 --station es/04/003/02/001/B --out proof.json
actasum log check-proof --proof proof.json --checkpoint checkpoint.txt
```

Quien construya el registro a partir del mismo ZIP obtiene el mismo punto de
control. Véase [`docs/spec/log.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/log.md).

### Firma y testigos

El registro puede firmar su punto de control, y un testigo puede cofirmarlo
tras comprobar que el registro solo ha crecido. Hace falta el paquete opcional
`cryptography` (`pip install -e '.[sign]'`).

```sh
# quien opera el registro
actasum key new --name actasum/es/congreso/2019-11 --out log.key      # muestra la clave pública del registro
actasum log sign --log log-2019-11 --key log.key
actasum log witness-request --log log-2019-11 --old-size 0 --out request.txt

# el testigo, idealmente otra organización en otra máquina
actasum witness init --dir witness --name witness.example/w1           # muestra la clave pública del testigo
actasum witness trust --dir witness --log-key '<clave pública del registro>'
actasum witness add-checkpoint --dir witness --request request.txt --out cosignature.txt

# de vuelta en el registro, y después cualquiera
actasum log cosign --log log-2019-11 --signatures cosignature.txt
actasum log check-checkpoint --checkpoint log-2019-11/checkpoint \
    --log-key '<clave pública del registro>' --witness-key '<clave pública del testigo>' --quorum 1
```

Un testigo se niega a cofirmar un registro que cambió o eliminó una entrada
que ya había visto. Eso solo significa algo cuando el testigo lo opera alguien
independiente de quien opera el registro; ejecutar ambos uno mismo demuestra
que el mecanismo funciona y nada más. Los formatos siguen las especificaciones
C2SP; véase [`docs/spec/witness.md`](https://github.com/arfonzeras/actasum/blob/main/docs/spec/witness.md) para lo que está
hecho y lo que no.

## Qué significa un resultado y qué no

- **Cuadra** significa que los totales publicados son la suma de las cifras
  por mesa publicadas. Es coherencia entre dos publicaciones, no
  verificación. Nada más.
- Una **diferencia** significa que no suman. No dice por qué: una corrección
  legal durante el escrutinio general, un error de transcripción y un fraude
  se ven igual desde aquí. Una diferencia es un motivo para preguntar, no una
  conclusión.
- En esta primera versión las dos entradas proceden de la misma autoridad.
  Que cuadren demuestra que sus dos publicaciones son coherentes entre sí. No
  demuestra que reflejen las actas en papel. Las capturas independientes de
  las actas son el objeto de los hitos siguientes.

## El diseño en un párrafo

Un núcleo independiente del país define la declaración de acta, los totales
oficiales y las reglas de verificación. Un perfil por país traduce la ley y
los datos locales al núcleo. España es el primer perfil porque sus resultados
son públicos hasta el nivel de mesa. Los hitos siguientes añaden un registro
de transparencia de solo añadir (un árbol de Merkle con testigos
independientes, como el que se usa para los certificados web), declaraciones
firmadas por observadores acreditados con credenciales verificables del W3C,
y varias capturas independientes por mesa.

## Hoja de ruta

1. **Formato y verificador** sobre una elección pasada, con datos públicos. *(ejecutado con elecciones de España, Colombia, México y Brasil)*
2. **Cargar una elección completa en un registro** y servir pruebas de inclusión. *(primera versión)*
3. Reproducir la segunda vuelta presidencial de Colombia de 2026 con los formularios E-14 publicados.
4. **Un testigo que cofirme el estado del registro.** *(mecanismo hecho; aún sin testigo externo)*
5. Credenciales y una aplicación de captura, con firma en el dispositivo y uso sin conexión.
6. Un piloto real y pequeño junto a una organización local de observación electoral.

## Ejecutar las pruebas

```sh
pip install pytest
pytest
```

## Fuentes de datos y agradecimientos

- Resultados electorales: Ministerio del Interior (España), *Área de
  descargas*; Registraduría Nacional del Estado Civil (Colombia), sitio de
  escrutinios; Instituto Nacional Electoral (México); Tribunal Superior
  Eleitoral (Brasil), portal de datos abiertos. Este repositorio no incluye
  datos electorales.
- El diseño de columnas de los ficheros del Ministerio se tomó primero del
  paquete de R [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
  de rOpenSpain, de Héctor Meleiro, y después se contrastó con el documento
  de diseño del propio Ministerio. No se incluye código de ese paquete.

## Licencia

[Apache License 2.0](https://github.com/arfonzeras/actasum/blob/main/LICENSE).
