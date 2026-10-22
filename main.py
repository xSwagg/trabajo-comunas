# main.py
# Punto de entrada CLI: lee CSVs, crea flota y ejecuta la optimización.

import csv
import os  #arma las rutas absolutas a los CSV para que funcionen desde cualquier carpeta
import sys  
import argparse #Para leer lo que escribo en la terminal

from algoritmos import cargar_mapa
from reparto import Paquete, Vehiculo, asignar_greedy, imprimir_plan

# Carpeta base = donde está este archivo, para que funcione desde cualquier directorio
BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description="Reparto en Ibagué: greedy + Dijkstra + programación dinámica")
    ap.add_argument("--vehiculos", default=os.path.join(BASE, "data", "vehiculos.csv"))
    ap.add_argument("--paquetes", default=os.path.join(BASE, "data", "paquetes.csv"))
    ap.add_argument("--rutas", default=os.path.join(BASE, "data", "rutas.csv"))
    ap.add_argument("--deposito", default="Comuna 1 - Centro")
    ap.add_argument("--turbo", type=int, default=3)
    ap.add_argument("--van", type=int, default=8)
    ap.add_argument("--moto", type=int, default=4)
    args = ap.parse_args()

    # 1) Leer catálogo de vehículos y crear unidades
    catalogo = {}
    with open(args.vehiculos, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            catalogo[fila["tipo"].strip().lower()] = tuple(float(fila[c]) for c in ("peso_max_kg", "largo_m", "ancho_m", "alto_m"))

    prefijos = {"turbo": "T", "van": "V", "moto": "M"}
    vehiculos = []
    for tipo, cantidad in [("turbo", args.turbo), ("van", args.van), ("moto", args.moto)]:
        if tipo not in catalogo:
            print(f"Error: tipo «{tipo}» no está en el catálogo", file=sys.stderr)
            return 1
        peso_max, largo, ancho, alto = catalogo[tipo]
        for n in range(1, cantidad + 1):
            vehiculos.append(Vehiculo(f"{prefijos[tipo]}-{n:02d}", tipo, peso_max, largo, ancho, alto))

    # 2) Leer paquetes
    paquetes = []
    with open(args.paquetes, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            paquetes.append(Paquete(
                fila["id"].strip(),
                float(fila["peso"]), float(fila["altura"]),
                float(fila["ancho"]), float(fila["profundidad"]),
                fila["ubicacion"].strip()))

    # 3) Cargar grafo y pre-calcula distancias mínimas (Dijkstra)
    mapa = cargar_mapa(args.rutas)
    if args.deposito not in mapa:
        print(f"Error: depósito «{args.deposito}» no existe en el grafo", file=sys.stderr)
        return 1

    # 4) Ejecutar asignación greedy + cálculo de rutas (DP + Dijkstra)
    plan, sin_asignar = asignar_greedy(vehiculos, paquetes, mapa, args.deposito)

    # 5) Imprimir resultados
    print("=" * 70)
    print(" OPTIMIZADOR DE FLOTA Y RUTAS — Ibagué (Tolima)")
    print("=" * 70)
    print(f"Métodos: GREEDY (asignación) | DIJKSTRA (distancias mínimas) | "
          f"PROG. DINÁMICA (Held-Karp, orden de ruta)")
    for tipo, (peso_max, largo, ancho, alto) in sorted(catalogo.items(),
            key=lambda i: -i[1][1]*i[1][2]*i[1][3]):
        print(f"  {tipo:<6} {peso_max:.0f} kg | {largo}x{ancho}x{alto} m = {largo*ancho*alto:.3f} m³")
    print(f"Flota: {len(vehiculos)} vehículos | Paquetes: {len(paquetes)} | Depósito: {args.deposito}")
    imprimir_plan(plan, sin_asignar, len(paquetes))
    return 0


if __name__ == "__main__":
    import csv
    sys.exit(main())
