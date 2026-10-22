# reparto.py
# GREEDY de asignación de paquetes a vehículos + empaquetado 3D (puntos extremos + AABB)

from collections import namedtuple #en vez de hacer una clase gigante, haces tuplas con nombre
from algoritmos import optimizar_ruta #Importa la función optimizar_ruta desde algoritmos.py (la que elige entre Held-Karp o Greedy según cuántas paradas hay).

Paquete = namedtuple("Paquete", "id peso altura ancho profundidad ubicacion")
Vehiculo = namedtuple("Vehiculo", "id tipo peso_max largo ancho alto")

EPS = 1e-9  # margen para errores de punto flotante (0.1+0.2 no es exacto)


def vol_paquete(p):
    return p.altura * p.ancho * p.profundidad


def vol_vehiculo(v):
    return v.largo * v.ancho * v.alto


class Bodega:
    """Espacio de carga: controla peso y 3D con puntos extremos + test AABB."""

    def __init__(self, vehiculo):
        self.veh = vehiculo
        self.puestos = []    # paquetes ya colocados: (paquete, x, y, z, dx, dy, dz)
        self.peso = 0.0
        self.puntos = [(0.0, 0.0, 0.0)]  # esquinas disponibles

    def libre(self):
        return vol_vehiculo(self.veh) - sum(dx * dy * dz for _, _, _, _, dx, dy, dz in self.puestos)

    def intentar(self, p):
        """Intenta colocar el paquete. True si cabe (peso + 3D), False si no."""
        v = self.veh
        if self.peso + p.peso > v.peso_max + EPS:
            return False  # excede peso
        # 6 rotaciones de la caja (permutaciones de sus dimensiones)
        d = (p.altura, p.ancho, p.profundidad)
        rots = {(d[i], d[j], d[k]) for i in range(3) for j in range(3) for k in range(3) if len({i, j, k}) == 3}
        mejor = None
        for (px, py, pz) in self.puntos:
            for dx, dy, dz in rots:
                if px + dx > v.largo + EPS or py + dy > v.ancho + EPS or pz + dz > v.alto + EPS:
                    continue  # no cabe en la bodega
                # test AABB: ¿choca con algún paquete ya puesto?
                if any(px < x + ddx and px + dx > x and py < y + ddy and py + dy > y
                       and pz < z + ddz and pz + dz > z
                       for _, x, y, z, ddx, ddy, ddz in self.puestos):
                    continue  # colisión
                clave = (pz, py, px, dx, dy, dz)  # prefiere el punto más bajo/cercano
                if mejor is None or clave < mejor[0]:
                    mejor = (clave, px, py, pz, dx, dy, dz)
        if not mejor:
            return False  # no cabe en ningún punto con ninguna rotación
        _, px, py, pz, dx, dy, dz = mejor
        self.puestos.append((p, px, py, pz, dx, dy, dz))
        self.peso += p.peso
        # Generar nuevos puntos extremos: a la derecha, arriba y al frente
        self.puntos = list(set(self.puntos) | {(px + dx, py, pz), (px, py + dy, pz), (px, py, pz + dz)})
        return True


def asignar_greedy(vehiculos, paquetes, mapa, deposito):
    """GREEDY de asignación:
    1) Zonas con mayor volumen demandado primero
    2) Paquetes más grandes primero
    3) Vehículo más pequeño que pueda cargarlo (peso + 3D)
    4) Prioriza vehículos que ya entregan en esa comuna (consolidar)
    """
    bodegas = [Bodega(v) for v in vehiculos]
    # Calcular demanda por comuna (volumen total)
    demanda = {}
    for p in paquetes:
        demanda[p.ubicacion] = demanda.get(p.ubicacion, 0.0) + vol_paquete(p)
    sin_asignar = []
    # Procesar primero las zonas con más demanda
    for zona in sorted(demanda, key=lambda z: -demanda[z]):
        # Dentro de la zona, paquetes más grandes primero
        for p in sorted([q for q in paquetes if q.ubicacion == zona], key=lambda q: -vol_paquete(q)):
            if p.ubicacion not in mapa:
                sin_asignar.append((p, "ubicación no existe en el grafo"))
                continue
            # Ordenar bodegas: más pequeña -> ya carga esa zona -> más espacio libre -> id
            orden = sorted(bodegas, key=lambda b: (
                vol_vehiculo(b.veh),
                0 if any(q.ubicacion == zona for q, *_ in b.puestos) else 1,
                -b.libre(),
                b.veh.id))
            for b in orden:
                if b.intentar(p):
                    break
            else:
                sin_asignar.append((p, "excede el peso o no cabe en ninguna bodega/vehiculo"))
    # Calcular ruta por vehículo cargado (DP si ≤15 paradas, si no greedy)
    plan = []
    for b in bodegas:
        if not b.puestos:
            continue
        zonas = sorted({q.ubicacion for q, *_ in b.puestos})
        ruta, km = optimizar_ruta(mapa, deposito, zonas)
        plan.append((b, ruta, km))
    plan.sort(key=lambda x: x[0].veh.id)
    return plan, sin_asignar


def imprimir_plan(plan, sin_asignar, total_paquetes):
    """Imprime el plan de entrega por vehículo y el resumen total."""
    print("=" * 70)
    print(" PLAN DE ENTREGA — Ibagué (Tolima)")
    print("=" * 70)
    for b, ruta, km in plan:
        v = b.veh
        usado = vol_vehiculo(v) - b.libre()
        print(f"\n[{v.id}] {v.tipo} — {len(b.puestos)} paquete(s)")
        print(f"  carga: {b.peso:.1f}/{v.peso_max:.1f} kg ({b.peso/v.peso_max*100:.1f}%) | "
              f"{usado:.3f}/{vol_vehiculo(v):.3f} m³")
        if len(set(ruta)) == 1:
            print(f"  ruta: reparto local en {ruta[0]}")
        else:
            print(f"  ruta: {' -> '.join(ruta)}")
        print(f"  km: {km:.1f}")
        for p in sorted((q for q, *_ in b.puestos), key=lambda q: q.id):
            print(f"    · {p.id} {p.peso:.1f} kg {p.altura:.2f}x{p.ancho:.2f}x{p.profundidad:.2f} m -> {p.ubicacion}")
    total = sum(len(b.puestos) for b, _, _ in plan)
    print("\n" + "-" * 70)
    print(f"Paquetes: {total}/{total_paquetes} | Vehículos cargados: {len(plan)} | "
          f"Peso movido: {sum(b.peso for b,_,_ in plan):.1f} kg")
    print(f"Distancia total: {sum(km for _,_,km in plan):.1f} km")
    if sin_asignar:
        print(f"\nSin asignar ({len(sin_asignar)}):")
        for p, motivo in sin_asignar:
            print(f"  · {p.id} {p.peso:.1f} kg [{p.ubicacion}]: {motivo}")
