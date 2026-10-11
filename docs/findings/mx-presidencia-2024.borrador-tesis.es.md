# Borrador retirado de la tesis: apartado 6.3, México

**Texto retirado de la tesis el 11 de octubre de 2026 y guardado aquí hasta
la fusión de la rama `profile-mx`.** Está desfasado y no debe citarse:

- Sus cifras son anteriores al cambio del núcleo para cifras no leídas. Las
  vigentes están en [`mx-presidencia-2024.md`](mx-presidencia-2024.md).
- Dice que el núcleo no se modificó. Ya no es cierto: México obligó a añadir
  `counts.unread`.
- Llama «casillas» a las celdas del acta, que en México significa mesa.
- No recoge el contraste con el comunicado del INE ni las 16 mesas con
  recuento y sin cifras en el cómputo.

En la fusión se reescribe con las cifras definitivas, junto con el resumen y
los capítulos 5, 7 y 8.

---

### 6.3 México

*Ejecución del 11 de octubre de 2026 en la rama `profile-mx` del repositorio,
sin fusionar y pendiente de confirmación del autor. El resumen y los
capítulos 5, 7 y 8 no la recogen todavía.*

México se añadió para responder a una pregunta: si un tercer país entra en el
formato sin cambiar el núcleo. Entra, y es el primer caso con declaraciones
reales tanto del recuento como de un acto posterior. Siete cosas no encajaron
y quedaron como límites del perfil. El detalle está en el informe de
hallazgos y en la especificación del perfil.

#### Dos publicaciones del mismo órgano

El perfil lee dos bases de datos del Instituto Nacional Electoral (INE) para
la elección presidencial del 2 de junio de 2024, según las describen sus
manuales (INE, 2024a; INE, 2024b):

- **El PREP** (Programa de Resultados Electorales Preliminares) captura las
  cifras de una copia del acta de cada casilla durante la noche electoral. El
  propio INE califica sus resultados de preliminares y no definitivos. Cada
  fila da una declaración del recuento de mesa.
- **Los cómputos distritales** recogen cada acta tal como la computaron los
  consejos distritales en los días siguientes, por cotejo de actas o por
  recuento de las papeletas. Cada fila da una declaración del escrutinio, que
  sustituye a la anterior.

Las dos comparaciones enfrentan publicaciones del INE entre sí. No se ha
mirado ningún acta ni se ha leído el resultado declarado.

#### Resultados

| Comprobación | Resultado |
| --- | --- |
| Las filas del PREP suman los totales que imprime su cabecera | Sí: 159.004 actas contabilizadas y 56.107.873 votos |
| Las filas de los cómputos suman los totales de su cabecera | Sí: 170.766 actas y 60.115.184 votos |
| Casillas con declaración de los dos actos | 138.799 |
| De ellas, con las mismas cifras | 52.078 |
| De ellas, con cifras distintas | 86.721 |
| Casillas en conflicto o indeterminadas | 0 |

En los cómputos, 116.397 de las 170.766 actas, el 68 %, están marcadas como
recuento de papeletas. De las 86.721 casillas que cambian, 84.260 fueron
recontadas y 2.461 solo cotejadas. En 7.084 el cambio mueve votos entre
columnas de una misma coalición y ninguna candidatura gana ni pierde.

Saldo del cómputo menos el PREP en las casillas que cambian:

| Concepto | Todas las casillas que cambian | De ellas, las 2.235 con más de 100 votos de cambio |
| --- | --- | --- |
| PVEM-PT-MORENA | +167.955 | +97.267 |
| PAN-PRI-PRD | −31.681 | −17.329 |
| MC | −12.310 | −16.694 |
| Candidaturas no registradas | −4.216 | −2.833 |
| Votos nulos | −41.022 | −14.377 |

El PREP no es el acta: es la captura de una copia. Una diferencia con el
cómputo puede ser un error de captura, una corrección o el resultado de
volver a contar las papeletas, y estos ficheros no permiten separarlos. Más
de la mitad del saldo mayor procede de 2.235 casillas, y ninguna de sus actas
se ha examinado. Entre las casillas solo cotejadas, donde el cómputo no
volvió a contar, el 5,1 % difiere del PREP.

#### Cifras que el PREP no pudo leer

El PREP contabiliza un acta cuando al menos una cifra es legible. En 20.160
actas contabilizadas hay 100.308 casillas marcadas «Sin dato» (93.167) o
«Ilegible» (7.141). El PREP las suma como cero. No las cuenta como votos
nulos: los nulos tienen su propia columna, que está a su vez entre las
ilegibles en 2.093 casos.

El cómputo permite ver qué había en esas casillas. De las marcadas «Sin
dato», 66.485 de 93.151 son cero en el cómputo; de las «Ilegible», 2.771 de
7.141. Entre todas suman 314.000 votos en el cómputo. Tratadas como cero, se
convierten en cambios que nadie hizo: las casillas con cifras distintas pasan
de 86.721 a 102.675.

Por eso el perfil, por defecto, no da declaración a esas actas. Una opción
las conserva con esas cifras a cero, y entonces la suma reproduce el total
que publica el propio PREP.

#### La prueba de neutralidad

El núcleo no se modificó. Las dos sumas, la cadena del recuento al escrutinio
y la lista de casillas que cambian salieron del núcleo tal como se escribió
para España y Colombia. Lo que no encajó, por orden de importancia:

1. **Una cifra ilegible no es un cero.** El núcleo solo admite enteros y
   trata igual un cero y una candidatura ausente. El perfil deja fuera 20.160
   actas.
2. **No hay cifra de votos en blanco.** El núcleo la exige y el perfil
   escribe cero, que es decir algo que el acta no dice.
3. **Una fila anterior, varias posteriores.** El PREP da el voto en el
   extranjero en una fila por estado y los cómputos por mesa de escrutinio,
   con otras claves. El núcleo sustituye una declaración por otra. El perfil
   deja fuera esas 32 filas para no sumar sus votos dos veces.
4. **Recuento o cotejo.** Que se volvieran a contar las papeletas cambia lo
   que significa una diferencia. El núcleo tiene un solo acto para ambos
   casos, y el perfil guarda la distinción donde el verificador no mira.
   Colombia ya anotaba lo mismo en cada modificación.
5. **Totales oficiales con solo un total general.** Los ficheros imprimen el
   total de votos, pero no un total por candidatura distinto de las propias
   filas. El formato de totales oficiales del núcleo no puede expresarlo.
6. **El total escrito en el acta** incluye nulos y candidaturas no
   registradas, y el núcleo solo tiene un total de candidaturas.
7. **Una huella por imagen de acta.** El núcleo declara pendiente la
   evidencia por imagen, y el perfil guarda la huella aparte.

Los puntos 1 y 3 cambian las cifras del apartado anterior. Si el núcleo debe
admitir alguno de los cuatro primeros, México no cumple el criterio de parada
del capítulo 9 y hace falta otro país para comprobarlo.
