# tallylog

[English](README.md) · **Español**

Un formato abierto y un verificador para las actas de escrutinio de las mesas
electorales.

Tras una elección, cada mesa anota su resultado en un acta. Después, la
autoridad electoral suma esas actas. `tallylog` permite que cualquiera repita
esa suma a partir de las cifras de cada mesa y la compare con los totales
publicados.

No se ocupa de la votación, de la identidad del votante ni de las papeletas.
Audita el tramo que va de la mesa al resultado publicado.

> **Estado: borrador inicial (v0.1).** El formato va a cambiar. El lector de
> España solo se ha probado con ficheros sintéticos y todavía no se ha
> ejecutado con una elección real. No te fíes de su salida.

Esta página es una traducción informativa. Si difiere del
[README en inglés](README.md), manda la versión inglesa.

## Qué hay aquí

| Ruta | Contenido |
| --- | --- |
| [`docs/spec/core.md`](docs/spec/core.md) | Formato y procedimiento de verificación, independientes del país (en inglés) |
| [`docs/spec/profile-es.md`](docs/spec/profile-es.md) | Perfil España: identificadores, fuente de datos, lagunas conocidas ([traducción](docs/spec/profile-es.es.md)) |
| [`schemas/statement.schema.json`](schemas/statement.schema.json) | Esquema JSON de una declaración de acta |
| `src/tallylog/` | Implementación de referencia, solo con la biblioteca estándar de Python |
| `tests/` | Pruebas con datos sintéticos |

## Inicio rápido

Requiere Python 3.10 o posterior. Sin dependencias.

```sh
pip install -e .
```

Descarga los ZIP de mesas (`_MESA`) y de totales (`_TOTA`) de una elección al
Congreso desde el
[área de descargas](https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/)
del Ministerio del Interior y ejecuta:

```sh
tallylog es replay --mesa 02201911_MESA.zip --tota 02201911_TOTA.zip
```

La orden indica cuántas circunscripciones cuadran y lista cada diferencia.
Termina con `0` si todo cuadra, con `1` si hay diferencias o lagunas, y con
`2` si no puede leer la entrada.

Lo mismo en pasos separados, generando los ficheros intermedios neutrales:

```sh
tallylog es convert  --mesa 02201911_MESA.zip --out statements.jsonl
tallylog es official --tota 02201911_TOTA.zip --out official.json
tallylog verify --statements statements.jsonl --official official.json
```

La salida del programa está en inglés.

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

1. **Formato y verificador** sobre una elección pasada, con datos públicos. *(este repositorio, en curso)*
2. Cargar una elección completa en un registro de transparencia y servir pruebas de inclusión.
3. Reproducir la segunda vuelta presidencial de Colombia de 2026 con los formularios E-14 publicados.
4. Un testigo externo que cofirme el estado del registro.
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
- El diseño de columnas de los ficheros del Ministerio se ha tomado del
  paquete de R [`infoelectoral`](https://github.com/rOpenSpain/infoelectoral)
  de rOpenSpain, de Héctor Meleiro. No se incluye código de ese paquete.

## Licencia

[Apache License 2.0](LICENSE).
