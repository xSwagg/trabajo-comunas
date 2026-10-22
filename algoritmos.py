# algoritmos.py
# ¿a cuántos km está el Salado desde la Comuna 1?" y "¿en qué orden visito estas paradas?".
# DIJKSTRA (distancias mínimas) + GREEDY (vecino más cercano) + PROGRAMACIÓN DINÁMICA (Held-Karp)

import csv  #Para leer y escribir archivos CSV
import math  #para inicializar la tabla DP con valores "imposiblemente grandes" y poder comparar mínimos

RUTA_MAX_DP = 15  # Held-Karp exacto hasta 15 paradas; más que eso usa greedy


def dijkstra(vecinos, origen):
    """Distancia mínima desde `origen` a todos los nodos del grafo."""
    #¿Y por qué Dijkstra y no Floyd-Warshall? Porque solo necesitamos las distancias desde unos orígenes específicos
    #no de todos contra todos. Y lo guarda en caché, o sea solo corre 13 veces máximo (una por comuna) y ya.

    dist = {n: (0.0 if n == origen else math.inf) for n in vecinos}
    visitados = set()
    while True:
        actual = min((n for n in vecinos if n not in visitados), key=dist.get, default=None)
        if actual is None or dist[actual] == math.inf:
            break
        visitados.add(actual)
        for vecino, km in vecinos[actual].items():
            if dist[actual] + km < dist[vecino]:  # relajar arista
                dist[vecino] = dist[actual] + km
    return dist


def cargar_mapa(ruta_csv):
    """Lee CSV (origen,destino,distancia_km), construye grafo no dirigido
    y pre-calcula distancias mínimas entre todos los pares (una vez)."""
    vecinos = {}
    with open(ruta_csv, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            a, b, km = fila["origen"].strip(), fila["destino"].strip(), float(fila["distancia_km"])
            vecinos.setdefault(a, {})[b] = km
            vecinos.setdefault(b, {})[a] = km
    # Pre-calcula distancias mínimas desde cada nodo (para no repetir Dijkstra)
    mapa = {n: dijkstra(vecinos, n) for n in vecinos}
    return mapa


def km_ruta(mapa, ruta):
    """Total de km de una ruta usando distancias mínimas (Dijkstra)."""
    return sum(mapa[a][b] for a, b in zip(ruta, ruta[1:]))


def ruta_greedy(mapa, deposito, zonas):
    """GREEDY de ruta (vecino más cercano): en cada paso va a la comuna pendiente más cercana."""
    ruta, actual, pendientes = [deposito], deposito, set(zonas)
    while pendientes:
        sig = min(pendientes, key=lambda z: mapa[actual][z])
        ruta.append(sig)
        pendientes.discard(sig)
        actual = sig
    ruta.append(deposito)
    return ruta, km_ruta(mapa, ruta)


def ruta_dp(mapa, deposito, zonas):
    """PROGRAMACIÓN DINÁMICA (Held-Karp): encuentra el orden de visita ÓPTIMO.

    dp[mascara][i] = km mínimos para visitar las comunas marcadas en `mascara`
    (bit i encendido = comuna i visitada) y terminar en la comuna i.
    Complejidad: O(2^n · n^2).
    """
    n = len(zonas)
    total = 1 << n
    dp = [[math.inf] * n for _ in range(total)]
    padre = [[None] * n for _ in range(total)]
    for i in range(n):
        dp[1 << i][i] = mapa[deposito][zonas[i]]  # base: ir del depósito a una sola comuna
    for mask in range(total):   #qué comunas ya visité codificado en bits
        for i in range(n):
            if not mask & (1 << i) or dp[mask][i] == math.inf:
                continue
            for j in range(n):
                if mask & (1 << j):
                    continue  # j ya visitada
                nueva = mask | (1 << j)
                cand = dp[mask][i] + mapa[zonas[i]][zonas[j]]
                if cand < dp[nueva][j]:
                    dp[nueva][j] = cand
                    padre[nueva][j] = i
    # Elegir mejor última comuna y volver al depósito
    mask = total - 1
    u = min(range(n), key=lambda i: dp[mask][i] + mapa[zonas[i]][deposito])
    orden = []
    while u is not None:
        orden.append(zonas[u])
        prev = padre[mask][u]
        mask ^= 1 << u
        u = prev
    orden.reverse()
    ruta = [deposito] + orden + [deposito]
    return ruta, km_ruta(mapa, ruta)


def optimizar_ruta(mapa, deposito, zonas):
    """Elige DP (óptimo) si ≤15 paradas; si no, greedy (vecino más cercano)."""
    lista = sorted(set(zonas) - {deposito})
    if not lista:
        return [deposito, deposito], 0.0
    if len(lista) <= RUTA_MAX_DP:
        return ruta_dp(mapa, deposito, lista)
    return ruta_greedy(mapa, deposito, lista)
