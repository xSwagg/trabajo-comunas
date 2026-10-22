# DOCUMENTACIÃÃN TÃÃCNICA Ã¢ââ Optimizador de Flota y Rutas (IbaguÃ©, Tolima)

Software de consola (sin interfaz grÃ¡fica) que resuelve: **Â¿quÃ© vehÃ­culos cargan quÃ© paquetes y por quÃ© orden de rutas se reparte?**

---

## 1. Problema que resuelve

Una empresa de transporte tiene:

- Una **flota** mixta (turbos, vans, motos) con distinto peso mÃ¡ximo y distinto tamaÃ±o de bodega.
- Un lote de **paquetes** con peso y dimensiones (largo Ãâ ancho Ãâ alto) y una **ubicaciÃ³n de entrega**.
- Un **grafo de la ciudad** (las 13 comunas de IbaguÃ©) con distancias entre comunas vecinas.

Debe decidir:

1. **AsignaciÃ³n**: quÃ© vehÃ­culo lleva cada paquete sin superar el peso ni el espacio (empaquetado 3D real, las cajas no se teleportan ni se solapan).
2. **Ruteo**: en quÃ© orden visita las comunas cada vehÃ­culo cargado, minimizando kilÃ³metros.

Esto es una versiÃ³n simplificada del **CVRP** (*Capacitated Vehicle Routing Problem*) con una restricciÃ³n de **bin packing 3D** en la carga. Ambos problemas son NP-difÃ­ciles, por eso se combinan mÃ©todos exactos (para partes pequeÃ±as) y heurÃ­sticas (para partes grandes).

---

## 2. Estructura de archivos

```
trabajo/
Ã¢âÅÃ¢ââÃ¢ââ main.py                 # todo el software (~470 lÃ­neas, con comentarios de guÃ­a)
Ã¢âÅÃ¢ââÃ¢ââ data/
Ã¢ââ   Ã¢âÅÃ¢ââÃ¢ââ vehiculos.csv       # catÃ¡logo de tipos de vehÃ­culo
Ã¢ââ   Ã¢âÅÃ¢ââÃ¢ââ paquetes.csv        # 25 paquetes de muestra en las comunas de IbaguÃ©
Ã¢ââ   Ã¢ââÃ¢ââÃ¢ââ rutas.csv           # grafo: aristas entre comunas con distancia_km
Ã¢ââÃ¢ââÃ¢ââ DOCUMENTACION.md        # este documento
```

### 2.1 `vehiculos.csv`

| tipo | peso_max_kg | largo_m | ancho_m | alto_m |
|---|---|---|---|---|
| turbo | 300 | 5.80 | 2.30 | 2.60 |
| van | 200 | 2.40 | 1.60 | 1.80 |
| moto | 30 | 0.50 | 0.50 | 0.50 |

Solo define **tipos**; las unidades concretas (T-01, T-02, V-01Ã¢âÂ¦) se generan en `main()` segÃºn los argumentos `--turbo`, `--van`, `--moto`.

### 2.2 `paquetes.csv`

Columnas: `id, peso, altura, ancho, profundidad, ubicacion`. La `ubicacion` debe ser el nombre exacto de un nodo del grafo (`Comuna 7 - Salado`, etc.). Ejemplo:

```csv
id,peso,altura,ancho,profundidad,ubicacion
P001,8.5,0.35,0.30,0.30,Comuna 1 - Centro
```

### 2.3 `rutas.csv`

Columnas: `origen, destino, distancia_km`. Cada arista se guarda **una sola fila** pero se interpreta en ambos sentidos (grafo no dirigido: en la ciudad se puede ir y volver por la misma vÃ­a). Las comunas sin arista directa se comunican **a travÃ©s de otras comunas**: la distancia entre ellas la resuelve Dijkstra (por ejemplo C1 Ã¢â â Salado = 9.2 km aunque no haya arista directa).

---

## 3. Flujo del programa (pipeline)

```
CSV flota Ã¢ââÃ¢âÂ
CSV paquetes Ã¢ââÃ¢âÂ¼Ã¢ââÃ¢âÂº GREEDY de asignaciÃ³n Ã¢ââÃ¢âÂº empaque 3D por vehÃ­culo Ã¢ââÃ¢âÂº zonas de cada vehÃ­culo
CSV rutas Ã¢ââÃ¢âË                                    Ã¢ââ
                                                Ã¢âÂ¼
                    DIJKSTRA (distancias mÃ­nimas en el grafo, cacheado)
                                                Ã¢ââ
                                                Ã¢âÂ¼
                    HELD-KARP / greedy (orden Ã³ptimo de visita por vehÃ­culo)
                                                Ã¢ââ
                                                Ã¢âÂ¼
                              Plan de entrega + resumen en consola
```

Paso a paso en `main()` (lÃ­neas numeradas 1Ã¢âÃ5 en el cÃ³digo):

1. **ParÃ¡metros** (`argparse`): rutas de los CSV, nombre del depÃ³sito (por defecto `Comuna 1 - Centro`) y cuÃ¡ntos vehÃ­culos de cada tipo hay.
2. **Flota**: leer catÃ¡logo y crear unidades `T-01Ã¢âÂ¦`, `V-01Ã¢âÂ¦`, `M-01Ã¢âÂ¦`.
3. **Datos**: leer paquetes (con validaciones: positivos, ids Ãºnicos, no vacÃ­os) y el grafo (distancias no negativas).
4. **OptimizaciÃ³n**: `asignar_greedy` Ã¢â â `optimizar_ruta` (Dijkstra + Held-Karp/greedy).
5. **Reporte**: encabezado, detalle por vehÃ­culo, vehÃ­culos ociosos, paquetes sin asignar con su motivo, totales (kg movidos, km totales).

Cualquier error de datos (archivo inexistente, medida negativa, depÃ³sito inexistente, tipo de vehÃ­culo no definido) termina con cÃ³digo de salida **1** y mensaje en stderr; un plan vÃ¡lido termina con **0**.

---

## 4. Los tres mÃ©todos pedidos (y por quÃ© cada uno)

### 4.1 GREEDY Ã¢ââ asignaciÃ³n de paquetes a vehÃ­culos (`asignar_greedy`)

**QuÃ© hace (reglas, en orden):**

1. Agrupa la demanda por comuna (volumen total mÃÂ³) y procesa primero las comunas con **mÃ¡s demanda**.
2. Dentro de cada comuna ordena los paquetes de **mayor a menor volumen**.
3. Cada paquete se prueba en los vehÃ­culos ordenados por esta clave voraz:
   - (a) **tipo mÃ¡s pequeÃ±o primero** (volumen total de la bodega): no usar un turbo para un paquete de moto;
   - (b) **consolidaciÃ³n**: si el vehÃ­culo ya lleva paquetes a esa misma comuna, gana prioridad (menos viajes, menos km);
   - (c) **equilibrio de carga**: entre iguales, el que tenga mÃ¡s espacio libre;
   - (d) **id** como desempate, para que el resultado sea siempre igual (determinista).
4. El paquete se coloca solo si cabe en **peso** y en **3D** (ver ÃÂ§4.4). Si ningÃºn vehÃ­culo lo admite, queda en la lista de no asignados con el motivo.

**Â¿Por quÃ© greedy y no un Ã³ptimo global?**

- El problema completo (asignaciÃ³n + ruteo) es NP-difÃ­cil; un Ã³ptimo exacto global serÃ­a inviable incluso para la muestra.
- El *biggest-first* (primero los paquetes/zonas grandes) es la regla clÃ¡sica de los algoritmos de bin packing; reduce la fragmentaciÃ³n de capacidad y deja los huecos pequeÃ±os para los paquetes pequeÃ±os.
- Es rÃ¡pido: para cada paquete se recorren los vehÃ­culos y se intenta colocar; con flotas reales (decenas de vehÃ­culos, miles de paquetes) corre en milisegundos.
- Es el mÃ©todo que usan en la prÃ¡ctica los WMS/ERP de bodega (reglas de asignaciÃ³n por prioridad).

**LimitaciÃ³n honesta:** la asignaciÃ³n no es Ã³ptima global; el resultado depende del orden. Por eso el orden de la clave de decisiÃ³n estÃ¡ pensado y documentado.

### 4.2 DIJKSTRA Ã¢ââ distancias mÃ­nimas (`dijkstra` + clase `Mapa`)

**QuÃ© hace:** desde un nodo origen calcula la distancia mÃ­nima a **todas** las comunas del grafo, recorriendo aristas (relajaciÃ³n). ImplementaciÃ³n clÃ¡sica sin heap: en cada paso elige el nodo no visitado mÃ¡s cercano y relaja sus aristas (`main.py:35`).

**Para quÃ© se usa:**

- `km_ruta` suma las distancias mÃ­nimas entre paradas consecutivas de una ruta. AsÃ­, aunque dos comunas no tengan arista directa, el km calculado es el del camino real mÃ¡s corto (puede cruzar comunas intermedias).
- `asignar_greedy` valida que la comuna del paquete sea **alcanzable** desde el depÃ³sito (distancia finita) antes de asignarlo.

**Â¿Por quÃ© Dijkstra y no FloydÃ¢âÃWarshall?**

- FloydÃ¢âÃWarshall calcula la matriz completa de todos contra todos `O(VÃÂ³)` aunque solo necesites unos pocos orÃ­genes.
- Dijkstra desde cada origen pedido es `O(VÃÂ·(V+E))` con esta implementaciÃ³n simple (o `O((E+V)ÃÂ·log V)` con heap) y aquÃ­ solo se piden orÃ­genes que realmente se usan (depÃ³sito + comunas con carga).
- Se aÃ±ade **cachÃ©** (`Mapa._cache`): la distancia C1Ã¢â âSalado se calcula una vez y se reutiliza en todos los vehÃ­culos que la necesiten; Dijkstra se ejecuta como mucho una vez por comuna origen (Ã¢ÃÂ¤13 veces).
- DidÃ¡cticamente, Dijkstra es el algoritmo de caminos mÃ­nimos "de un origen" que se enseÃ±a en algoritmos; FloydÃ¢âÃWarshall es "todos contra todos" y aquÃ­ serÃ­a desperdicio.

**Nota:** el grafo de IbaguÃ© es pequeÃ±o, asÃ­ que la diferencia de tiempo es trivial; la elecciÃ³n es por claridad conceptual y escalabilidad.

### 4.3 PROGRAMACIÃÃN DINÃÂMICA Ã¢ââ Held-Karp para el orden de ruta (`ruta_dp`)

**QuÃ© problema resuelve:** dado el depÃ³sito y las comunas que debe visitar un vehÃ­culo, Â¿en quÃ© orden visita para minimizar km (ida y vuelta al depÃ³sito)? Es el TSP (problema del viajante) sobre esas paradas.

**CÃ³mo funciona la DP (Held-Karp):**

- `n` = nÃºmero de comunas del vehÃ­culo (sin contar el depÃ³sito).
- `mascara` = entero de `n` bits; bit `i` encendido = "la comuna `i` ya fue visitada". Hay `2Ã¢ÂÂ¿` mÃ¡scaras (todos los subconjuntos).
- `dp[mascara][i]` = **km mÃ­nimos** para salir del depÃ³sito, visitar exactamente las comunas de `mascara` y **terminar en la comuna `i`**.
- TransiciÃ³n: de un estado ya resuelto, "agregar" la comuna `j` pendiente: `dp[mascara | (1<<j)][j] = min(dp[mascara | (1<<j)][j], dp[mascara][i] + dist(iÃ¢â âj))`.
- Caso base: `dp[1<<i][i] = dist(deposito Ã¢â â i)`.
- Final: se cierra el ciclo elegiendo la mejor Ãºltima comuna `i` y sumando `dist(i Ã¢â â deposito)`.
- **ReconstrucciÃ³n:** la matriz `padre[mascara][i]` guarda desde quÃ© comuna se llegÃ³ a `i`; se retrocede hasta el origen y se invierte la lista.
- Las distancias `dist(iÃ¢â âj)` salen del **cachÃ© de Dijkstra** (ÃÂ§4.2).

**Complejidad:** tiempo `O(2Ã¢ÂÂ¿ ÃÂ· nÃÂ²)`, memoria `O(2Ã¢ÂÂ¿ ÃÂ· n)`. Por eso `RUTA_MAX_DP = 15`: `2ÃÂ¹Ã¢ÂÂµÃÂ·15ÃÂ² Ã¢ÃË 7,4 millones` de operaciones (instantÃ¡neo). Con `n = 20` ya serÃ­an ~400 millones.

**Â¿Por quÃ© exacta (y no 2-opt u otra metaheurÃ­stica)?**

- Para `n Ã¢ÃÂ¤ 15` la DP da la ruta **Ã³ptima exacta**, no "casi Ã³ptima". No hay riesgo de quedar atrapada en un Ã³ptimo local.
- El greedy vecino mÃ¡s cercano (ÃÂ§4.4 siguiente) puede ser 20Ã¢âÃ30 % peor (en las pruebas: 37.2 km vs 29.4 km en una ruta de 9 comunas).
- 2-opt solo mejora una ruta inicial de forma local; Held-Karp la resuelve completa. (En versiones anteriores del proyecto se usÃ³ 2-opt; se reemplazÃ³ porque el problema por vehÃ­culo es pequeÃ±o y la DP es exacta y mÃ¡s elegante.)

**Respaldo:** si una ruta superara las 15 paradas, `optimizar_ruta` cae automÃ¡ticamente a `ruta_greedy` (vecino mÃ¡s cercano, `O(nÃÂ²)` con consultas O(1) al cachÃ© de Dijkstra). Con los datos de IbaguÃ© (13 comunas) esto nunca ocurre, pero el cÃ³digo lo contempla.

### 4.4 GREEDY de ruta Ã¢ââ vecino mÃ¡s cercano (`ruta_greedy`)

MÃ©todo clÃ¡sico de construcciÃ³n: empezar en el depÃ³sito e ir siempre a la parada pendiente **mÃ¡s cercana** (segÃºn Dijkstra); al final volver al depÃ³sito. `O(nÃÂ²)` sin estructuras auxiliares. Ventaja: siempre devuelve una ruta vÃ¡lida; desventaja: no garantiza el Ã³ptimo (se usa solo como respaldo de la DP).

### 4.5 Empaquetado 3D Ã¢ââ heurÃ­stica de puntos extremos (`Bodega`)

No basta el peso: una moto tiene 0.125 mÃÂ³; si los paquetes no caben **geomÃ©tricamente**, no se cargan.

**RestricciÃ³n de peso:** `peso_acumulado + peso Ã¢ÃÂ¤ peso_max` (con epsilon `1e-9` por errores de coma flotante: `0.1+0.2 != 0.3` exactamente en binario).

**RestricciÃ³n de espacio (colocaciÃ³n voraz de cajas):**

1. Cada bodega mantiene una lista de **puntos extremos**: esquinas donde se puede apoyar la siguiente caja. Se inicia con el origen `(0,0,0)`.
2. Al colocar una caja en `(px,py,pz)` con medidas `(dx,dy,dz)`, se generan 3 puntos nuevos: a su derecha, encima y al frente. Se **deduplican** con un `set` (importante: en una versiÃ³n anterior se "podaban" puntos dominados y eso dejaba solo el origen, bloqueando todo).
3. Para cada paquete se prueban todas las **6 rotaciones** posibles de la caja (permutaciones de alto/ancho/profundidad; las rotaciones con espejo no agregan formas nuevas para un paralelepÃ­pedo alineado).
4. Una combinaciÃ³n (punto, rotaciÃ³n) es vÃ¡lida si:
   - la caja **cabe en la bodega** (no sobresale de largo/ancho/alto);
   - **no choca** con ningÃºn paquete ya puesto: test AABB (*axis-aligned bounding box*): dos cajas se solapan si sus proyecciones se intersecan en los tres ejes a la vez (`main.py:133-136`).
5. Entre las combinaciones vÃ¡lidas se elige la "mejor" con clave `(pz, py, px, Ã¢âÂ¦)`: prefiere el punto **mÃ¡s bajo** y mÃ¡s cercano al origen (apilar estable y ordenado).
6. Si no hay combinaciÃ³n vÃ¡lida, el paquete no cabe en ese vehÃ­culo.

**Â¿Por quÃ© esta heurÃ­stica?** El bin packing 3D es NP-difÃ­cil; los empaquetadores comerciales (y la literatura de *3D bin packing*) usan variantes de puntos extremos + reglas de preferencia. Es simple, rÃ¡pida y respeta la fÃ­sica bÃ¡sica (sin solapes, sin rotaciones imposibles).

**Dato de la muestra:** `P025` mide **6.00 m** de largo y ningÃºn vehÃ­culo llega a eso (el turbo tiene 5.80 m), por eso siempre aparece como no asignado: es un "paquete imposible" que sirve para mostrar el manejo de excepciones de negocio.

---

## 5. Decisiones de diseÃ±o

| DecisiÃ³n | RazÃ³n |
|---|---|
| Un solo archivo `main.py` | El proyecto se pidiÃ³ como herramienta de consola compacta; se fusionaron los mÃ³dulos iniciales (`flota.py`, `paquete.py`, Ã¢âÂ¦) en uno solo, comentado. |
| `namedtuple` para `Paquete` y `Vehiculo` | Inmutables, con acceso por nombre (`p.peso`), sin escribir clases completas; ideales para datos de solo lectura. |
| Sin dependencias externas (solo stdlib) | Corre en cualquier Python 3 sin `pip install`; `argparse`, `csv`, `math` cubren todo. |
| Grafo no dirigido | Las vÃ­as de la ciudad se recorren en ambos sentidos con la misma distancia de referencia. |
| CachÃ© de Dijkstra en `Mapa` | Evita recalcular distancias idÃ©nticas en cada vehÃ­culo; el grafo no cambia durante la ejecuciÃ³n. |
| Desempates por `id` | Resultados reproducibles: dos ejecuciones con los mismos CSV dan exactamente el mismo plan (importante para depurar y para calificar). |
| Epsilon `1e-9` en comparaciones de peso/medidas | Evita falsos rechazos por coma flotante. |
| `sys.stdout.reconfigure(encoding="utf-8")` | Evita el error de tildes/Ã± en consola de Windows (mojibake). |
| Validaciones y cÃ³digo de salida | Un CSV malformado termina con `exit 1` y mensaje claro; Ãºtil para automatizaciÃ³n. |

---

## 6. CÃ³mo ejecutarlo

```bash
# Flujo completo con los CSV de ejemplo (3 turbo, 8 van, 4 moto)
python main.py

# Flota reducida
python main.py --turbo 1 --van 2 --moto 1

# Otros archivos o depÃ³sito
python main.py --paquetes data/paquetes.csv --rutas data/rutas.csv --deposito "Comuna 1 - Centro"
```

Salida esperada (resumen): `Paquetes: 24/25 distribuidos | vehÃ­culos cargados: 12/15 | peso movido: 670.4 kg | Distancia total: 132.0 km`.

---

## 7. Complejidades resumidas

| Parte | Algoritmo | Complejidad |
|---|---|---|
| AsignaciÃ³n | Greedy biggest-first | `O(P ÃÂ· V ÃÂ· C)` en la prÃ¡ctica, con `C` = costo de intentar colocar (puntos extremos Ãâ 6 rotaciones Ãâ paquetes ya puestos) |
| Caminos mÃ­nimos | Dijkstra (por origen, cacheado) | `O(VÃÂ·(V+E))` por origen; Ã¢ÃÂ¤ V cÃ¡lculos totales |
| Orden de ruta | Held-Karp | `O(2Ã¢ÂÂ¿ÃÂ·nÃÂ²)` tiempo, `O(2Ã¢ÂÂ¿ÃÂ·n)` memoria, con `n Ã¢ÃÂ¤ 15` |
| Orden de ruta (respaldo) | Vecino mÃ¡s cercano | `O(nÃÂ²)` |
| ColocaciÃ³n 3D | Puntos extremos + 6 rotaciones + AABB | `O(k ÃÂ· P ÃÂ· r)` por intento, con `k` puntos y `r = 6` rotaciones |

Con `V = 13` comunas, `P = 25` paquetes, `Veh Ã¢ÃÂ¤ 15` vehÃ­culos: el programa termina en menos de un segundo.

---

## 8. Limitaciones (honestidad acadÃ©mica)

- La asignaciÃ³n greedy no garantiza el mÃ­nimo nÃºmero de vehÃ­culos ni el mÃ­nimo km global.
- No hay ventanas de tiempo, prioridades, ni restricciÃ³n de nÃºmero de paradas por vehÃ­culo.
- Las distancias del CSV son estimaciones de referencia de las comunas oficiales de IbaguÃ© (editables en `data/rutas.csv`).
- El empaquetado ignora forma del paquete (todo es caja), fragilidad, y asume suelo plano sin gravedad apilada por peso (solo geometrÃ­a).
- Held-Karp es exacto **por ruta**, condicionado al reparto ya hecho; no optimiza reparto y ruta a la vez.

---

## 9. Preguntas del profesor con respuestas (guÃ­a de estudio)

**P1. Â¿Por quÃ© usaste Dijkstra si el grafo es tan pequeÃ±o y podrÃ­as usar FloydÃ¢âÃWarshall?**
R. FloydÃ¢âÃWarshall calcula todos los pares (`O(VÃÂ³)`) aunque solo se necesiten unos pocos orÃ­genes. Dijkstra calcula solo los orÃ­genes que se usan (depÃ³sito y comunas con carga) y, ademÃ¡s, los resultados se cachean en `Mapa._cache`; en la prÃ¡ctica Dijkstra corre Ã¢ÃÂ¤13 veces. Es mÃ¡s eficiente en memoria y escalable si la ciudad crece. Con 13 nodos la diferencia es trivial, pero la elecciÃ³n es conceptualmente correcta: necesitamos caminos mÃ­nimos de un origen, no todos contra todos.

**P2. Â¿CuÃ¡l es la complejidad de Held-Karp y por quÃ© el lÃ­mite de 15 paradas?**
R. Tiempo `O(2Ã¢ÂÂ¿ÃÂ·nÃÂ²)`, memoria `O(2Ã¢ÂÂ¿ÃÂ·n)` por la tabla de subconjuntos (cada mÃ¡scara de bits es un subconjunto de comunas). Con `n=15`: ~2ÃÂ¹Ã¢ÂÂµÃÂ·225 Ã¢ÃË 7,4 M operaciones y unos pocos MB de RAM; con `n=20` serÃ­an ~4Ãâ10Ã¢ÂÂ¸ operaciones. Por eso `RUTA_MAX_DP=15`; si una ruta lo supera, el cÃ³digo cae a greedy vecino mÃ¡s cercano `O(nÃÂ²)`.

**P3. Â¿El resultado global es Ã³ptimo?**
R. No en el sentido global. El orden de ruta **de cada vehÃ­culo es Ã³ptimo exacto** (Held-Karp) condicionado a las paradas que le tocaron. La **asignaciÃ³n** paqueteÃ¢â âvehÃ­culo es greedy, no Ã³ptima. Es la descomposiciÃ³n clÃ¡sica del CVRP: resolver exactamente la parte pequeÃ±a (TSP por ruta) y usar heurÃ­stica en la parte combinatoria grande (asignaciÃ³n).

**P4. Â¿Por quÃ© no usaste fuerza bruta para la ruta?**
R. Fuerza bruta prueba `n!` Ã³rdenes (para 15 paradas, ~1.3Ãâ10ÃÂ¹ÃÂ²). Held-Karp reutiliza soluciones de subproblemas vÃ­a programaciÃ³n dinÃ¡mica sobre subconjuntos y baja a `2Ã¢ÂÂ¿ÃÂ·nÃÂ²`. Misma respuesta exacta, millones de veces menos trabajo.

**P5. Â¿Por quÃ© greedy para asignar y no un solver de programaciÃ³n entera?**
R. Un MIP/ILP exigirÃ­a dependencias externas (PuLP, GurobiÃ¢âÂ¦), tiempo de resoluciÃ³n impredecible y es menos didÃ¡ctico. El greedy biggest-first + consolidaciÃ³n por zona es el mÃ©todo usado en la industria (WMS), es determinista, corre en milisegundos y da soluciones de buena calidad. Se documentÃ³ su heurÃ­stica y sus lÃ­mites.

**P6. Â¿CÃ³mo evitas que las cajas se solapen en la bodega?**
R. Con un test AABB: dos cajas axis-aligned se intersecan solo si sus intervalos se solapan simultÃ¡neamente en X, Y y Z. Antes de colocar se comprueba que la nueva caja no interseca a ninguna ya puesta, ni sobresale de la bodega. AdemÃ¡s, cada paquete se prueba en 6 rotaciones posibles (permutaciones de sus dimensiones).

**P7. Â¿QuÃ© son los "puntos extremos" y por quÃ© no solo el origen?**
R. Es la heurÃ­stica clÃ¡sica del bin packing 3D: al colocar una caja aparecen 3 nuevas esquinas candidatas (derecha, arriba, al frente). Sin generar esos puntos, solo se podrÃ­a apilar todo en `(0,0,0)` y nada mÃ¡s entrarÃ­a. (De hecho, una versiÃ³n anterior del proyecto tenÃ­a ese bug al "podar" puntos dominados: dejaba solo el origen y bloqueaba el resto del espacio.)

**P8. Â¿Por quÃ© sumas con Dijkstra entre paradas si en el CSV hay aristas directas?**
R. El CSV solo lista **conexiones directas** entre comunas vecinas. Dos comunas sin arista comparten camino pasando por otras (p. ej. C1Ã¢â âSalado cruza comunas intermedias = 9.2 km). `km_ruta` usa siempre la distancia del camino mÃ¡s corto que Dijkstra ya calculÃ³, no la de una arista inexistente.

**P9. Â¿QuÃ© pasa si el grafo estÃ¡ desconectado o hay una comuna inalcanzable?**
R. Dijkstra deja esa distancia en infinito. Antes de asignar, `asignar_greedy` verifica `dist_deposito[ubicacion] != math.inf`; si no es alcanzable, el paquete queda en la lista de no asignados con el motivo "zona inaccesible", sin romper el programa.

**P10. Â¿Por quÃ© el greedy de asignaciÃ³n ordena primero las zonas de mayor volumen?**
R. Regla *biggest-first* de los algoritmos de bin packing: atacar primero la mayor demanda evita fragmentar la capacidad con paquetes chicos y luego no poder acomodar los grandes. Es anÃ¡logo a llenar primero el camiÃ³n con los bultos grandes y usar los huecos para los pequeÃ±os.

**P11. Â¿QuÃ© papel juega el "consolidar" (preferir el vehÃ­culo que ya va a esa comuna)?**
R. Reduce km y vehÃ­culos: si la moto M-03 ya visita Salado, un paquete extra para Salado cuesta ~0 km extra en lugar de un viaje nuevo. Es la clave greedy mÃ¡s importante para la calidad del ruteo.

**P12. Â¿El paquete P025 aparece sin asignar siempre? Â¿Es un error del programa?**
R. No es un bug: mide 6.00 m de largo y el vehÃ­culo mÃ¡s grande (turbo) tiene 5.80 m de bodega. NingÃºn vehÃ­culo puede contenerlo geomÃ©tricamente. El programa lo reporta como no asignado con el motivo "excede el peso o no cabe en ninguna bodega" Ã¢ââ asÃ­ debe comportarse un sistema real (rechazar y explicar, no tragar el error).

**P13. Â¿Por quÃ© `RUTA_MAX_DP` usa greedy de respaldo si con 13 comunas nunca se activa?**
R. Robustez: el cÃ³digo debe funcionar si el usuario edita el CSV y agrega comunas, o si un vehÃ­culo termina con muchas paradas. Un algoritmo que solo funciona con los datos de demostraciÃ³n no sirve en producciÃ³n.

**P14. Â¿QuÃ© problema exacto modela esto?**
R. Un CVRP (Capacitated VRP) con depÃ³sito Ãºnico, flota heterogÃ©nea, sin ventanas de tiempo, con ida y vuelta obligatoria al depÃ³sito, y con la restricciÃ³n de carga modelada como bin packing 3D por vehÃ­culo (no solo capacidad de peso). Sin ida/vuelta serÃ­a solo ruteo; sin capacidad serÃ­a TSP; con muchas capacidades y flota mixta, CVRP.

**P15. Â¿Por quÃ© no usaste una librerÃ­a de ruteo (Google OR-Tools, etc.)?**
R. El objetivo del trabajo es implementar y entender los algoritmos (greedy, Dijkstra, DP). Una librerÃ­a serÃ­a una caja negra. AdemÃ¡s, el requisito del curso es Python puro sin dependencias; el cÃ³digo asÃ­ corre en cualquier mÃ¡quina sin instalar nada.

**P16. Â¿Dijkstra con heap serÃ­a mejor? Â¿Por quÃ© no lo hiciste?**
R. SÃ­, con `heapq` pasarÃ­a de `O(VÃÂ²)` a `O((E+V) log V)`. Con 13 nodos la diferencia es despreciable; se eligiÃ³ la versiÃ³n simple sin heap por claridad didÃ¡ctica (menos cÃ³digo que mantener, mismo resultado). La interfaz (`dijkstra(vecinos, origen) -> dict`) permitirÃ­a cambiar la implementaciÃ³n sin tocar el resto.

**P17. Â¿Por quÃ© se permite que varios vehÃ­culos repartan en la misma comuna en vez de agrupar todo en uno?**
R. Por la capacidad: si un turbo no alcanza para todo el volumen/peso de esa comuna, hay que repartir. El greedy intenta consolidar (clave (b) del orden), pero la capacidad manda. AdemÃ¡s, repartir en paralelo entre varios vehÃ­culos es realista operativamente.

**P18. Â¿CÃ³mo garantizas que dos ejecuciones den el mismo plan?**
R. Todos los Ã³rdenes tienen desempate determinista: paquetes por id, vehÃ­culos por id, comunas por nombre. No hay aleatoriedad (ni `random`) en el pipeline. Es esencial para reproducir resultados al depurar o al calificar.

**P19. Â¿QuÃ© es el epsilon 1e-9 en las comparaciones?**
R. Las fracciones binarias (0.1, 0.2Ã¢âÂ¦) no son exactas en coma flotante; sin margen, `0.1+0.2 > 0.3` podrÃ­a rechazar un paquete que sÃ­ cabe. El epsilon tolera esos errores de redondeo en sumas de peso y medidas.

**P20. Â¿CuÃ¡les son las mÃ©tricas que imprime el plan y quÃ© significan?**
R. Por vehÃ­culo: carga en kg y en % del peso mÃ¡ximo; volumen usado en mÃÂ³ y % de la bodega; ruta (secuencia de comunas) y km totales (suma de caminos mÃ­nimos Dijkstra). Global: paquetes distribuidos, vehÃ­culos cargados, peso movido y distancia total de reparto. Son los KPIs tÃ­picos de planificaciÃ³n de reparto: ocupaciÃ³n de flota y costo de distancia.

**P21. Â¿El sistema optimiza km y nÃºmero de vehÃ­culos a la vez?**
R. No; son objetivos en tensiÃ³n. El greedy prioriza no dejar paquetes sin asignar y consolidar zonas; la DP minimiza km **por vehÃ­culo**. En la prÃ¡ctica, consolidar bien (menos vehÃ­culos) y rutar bien (menos km por vehÃ­culo) mejoran ambos, pero no hay una funciÃ³n objetivo Ãºnica global.

**P22. Â¿CÃ³mo cambiarÃ­a el programa si hubiera ventanas de tiempo o prioridades?**
R. En Held-Karp se agregarÃ­a un parÃ¡metro "hora de llegada" por estado (DP espacio-tiempo) o restricciones de precedencia; en la asignaciÃ³n, el orden greedy pasarÃ­a a incluir prioridad de la zona. La arquitectura (asignar Ã¢â â rutar Ã¢â â reportar) se mantiene; solo cambian las claves de decisiÃ³n y la DP.

---

## 10. VerificaciÃ³n realizada

- `python main.py`: 24/25 paquetes, 12/15 vehÃ­culos, 670.4 kg, 132.0 km.
- `python main.py --turbo 1 --van 2 --moto 1`: 24/25, 4/4 vehÃ­culos, 76.5 km.
- Dijkstra: C1Ã¢â âSalado 9.2 km; C1Ã¢â âBoquerÃ³n 4.7 km; C1Ã¢â âRicaurte 2.2 km.
- Held-Karp vs greedy en ruta de 9 comunas: 29.4 km vs 37.2 km (DP siempre Ã¢ÃÂ¤ greedy).
- CSV inexistente Ã¢â â mensaje de error y cÃ³digo de salida 1.
- `P025` (6 m) siempre reportado como no asignado con motivo claro.
