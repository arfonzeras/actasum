# actasum

[English](README.md) · **Español**

*Antes `tallylog`; renombrado el 11 de octubre de 2026.*

Un formato abierto y un verificador para las actas de escrutinio de las mesas
electorales.

Tras una elección, cada mesa anota su resultado en un acta. Después, la
autoridad electoral suma esas actas. `actasum` permite que cualquiera repita
esa suma a partir de las cifras de cada mesa y la compare con los totales
publicados.

No se ocupa de la votación, de la identidad del votante ni de las papeletas.
Audita el tramo que va de la mesa al resultado publicado.

> **Estado: borrador inicial (v0.1).** El formato va a cambiar. El lector de
> España se ha ejecutado hasta ahora con cinco elecciones reales (véase más
> abajo). No te fíes todavía de su salida para nada más.

Esta página es una traducción informativa. Si difiere del
[README en inglés](README.md), manda la versión inglesa.

## Resultados hasta ahora

El 11 de octubre de 2026 se ejecutó el verificador con los ficheros por mesa
del Ministerio del Interior de cinco elecciones al Congreso.

| Elección | Mesas | Circunscripciones cuyos totales recalculados cuadran |
| --- | --- | --- |
| Marzo de 2008 | 59.346 | 50 de 52 |
| Junio de 2016 | 57.531 | 52 de 52 |
| Abril de 2019 | 60.038 | 52 de 52 |
| Noviembre de 2019 | 59.555 | 52 de 52 |
| Julio de 2023 | 60.314 | 50 de 52 |

Donde los totales cuadran, coinciden los votos en blanco, los nulos, los
votos de cada candidatura y el número de mesas. En las cuatro
circunscripciones que difieren, los municipios siguen cuadrando con sus
mesas; la diferencia está en la fila del voto exterior. Los detalles y las
cautelas están en
[`docs/findings/es-congreso.md`](docs/findings/es-congreso.md) (en inglés).

Estas ejecuciones comparan las publicaciones del Ministerio entre sí. No
demuestran que las cifras por mesa coincidan con las actas en papel, y una
diferencia no dice cuál de las dos cifras publicadas es la correcta.

## Qué hay aquí

| Ruta | Contenido |
| --- | --- |
| [`docs/spec/core.md`](docs/spec/core.md) | Formato y procedimiento de verificación, independientes del país (en inglés) |
| [`docs/spec/log.md`](docs/spec/log.md) | Registro de solo añadir: puntos de control y pruebas de inclusión y de consistencia (en inglés) |
| [`docs/spec/witness.md`](docs/spec/witness.md) | Puntos de control firmados y testigos que los cofirman (en inglés) |
| [`docs/spec/profile-es.md`](docs/spec/profile-es.md) | Perfil España: identificadores, fuente de datos, lagunas conocidas ([traducción](docs/spec/profile-es.es.md)) |
| [`schemas/statement.schema.json`](schemas/statement.schema.json) | Esquema JSON de una declaración de acta |
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
momento se ha ejecutado una elección de cada tipo; véase
[`docs/findings/es-other-elections.md`](docs/findings/es-other-elections.md)
(en inglés). Para un primer vistazo a un ZIP:

```sh
actasum es describe --mesa 07202406_MESA.zip
```

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
control. Véase [`docs/spec/log.md`](docs/spec/log.md).

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
C2SP; véase [`docs/spec/witness.md`](docs/spec/witness.md) para lo que está
hecho y lo que no.

## Qué significa un resultado y qué no

- **Cuadra** significa que los totales publicados de la circunscripción son
  la suma de las cifras de las mesas. Nada más.
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

1. **Formato y verificador** sobre una elección pasada, con datos públicos. *(hecho para cinco elecciones al Congreso)*
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

- Resultados electorales: Ministerio del Interior, *Área de descargas*. Este
  repositorio no incluye datos electorales.
- El diseño de columnas de los ficheros del Ministerio se tomó primero del
  paquete de R [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
  de rOpenSpain, de Héctor Meleiro, y después se contrastó con el documento
  de diseño del propio Ministerio. No se incluye código de ese paquete.

## Licencia

[Apache License 2.0](LICENSE).
