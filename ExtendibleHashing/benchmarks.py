import time
import os
from extendible_hashing import HashIndex, Registro, D, BUCKET_FORMAT
import csv
from struct import calcsize
import random

CSV_FILE = "../data/cities_250k.csv"
INDEX_FILE = "benchmark_index.bin"
DATA_FILE = "benchmark_data.bin"
ENCODING = "ISO-8859-1"

def count_buckets(data_filename, bucket_size):
    size = os.path.getsize(data_filename)
    return size // bucket_size

def obtener_ids_desde_csv(filename, cantidad=100):
    ids = []
    with open(filename, newline='', encoding=ENCODING) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            ids.append(int(row[0]))
    return random.sample(ids, cantidad)

def main():
    # Eliminar archivos anteriores si existen
    if os.path.exists(INDEX_FILE):
        os.remove(INDEX_FILE)
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)

    hash_index = HashIndex(INDEX_FILE, DATA_FILE)

    t0 = time.time()
    count = 0

    with open(CSV_FILE, newline='', encoding=ENCODING) as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # saltar encabezado

        for row in reader:
            reg = Registro(
                int(row[0]), row[1], int(row[2]), row[3], row[4],
                int(row[5]), row[6], row[7],
                float(row[8]), float(row[9]), row[10]
            )
            hash_index.insert(reg)
            count += 1

    t1 = time.time()

    print(f"Insert {count} registros en {(t1 - t0):.2f} segundos")

    # Estadísticas
    bucket_size = calcsize(BUCKET_FORMAT)
    total_buckets = count_buckets(DATA_FILE, bucket_size)

    print(f"Buckets creados: {total_buckets}")
    print(f"Entradas en el índice: {len(hash_index.index)}")
    print(f"Tamaño archivo índice: {os.path.getsize(INDEX_FILE)/10**6:.2f} MB")
    print(f"Tamaño archivo buckets: {os.path.getsize(DATA_FILE)/10**6:.2f} MB")

    # Seleccionar IDs aleatorios
    keys = obtener_ids_desde_csv(CSV_FILE, 100)

    # Búsquedas
    t0 = time.time()
    for key in keys:
        hash_index.search(key)
    t1 = time.time()
    elapsed_search = ((t1 - t0) * 1000) / len(keys)
    print(f"Tiempo promedio de búsqueda: {elapsed_search:.2f} ms")

    # Eliminaciones
    t0 = time.time()
    for key in keys:
        hash_index.remove(key)  # 🔁 corregido: era search
    t1 = time.time()
    elapsed_remove = ((t1 - t0) * 1000) / len(keys)
    print(f"Tiempo promedio de eliminación: {elapsed_remove:.2f} ms")

if __name__ == "__main__":
    main()
