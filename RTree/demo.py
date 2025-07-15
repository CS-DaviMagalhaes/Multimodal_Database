from record import FixedRecord
from registro import Registro
import csv
import os
import time
import random

# Start cleanup
for ext in ["dat", "free.dat", "rtree.dat", "rtree.idx", "rtree.meta.dat"]:
    try: os.remove(f"demo_file.{ext}")
    except: pass

csv_path = os.path.join(os.path.dirname(__file__), '..', 'data')
csv_path = os.path.normpath(csv_path)

files = [os.path.join(csv_path, i) for i in os.listdir(csv_path)]
# 0: cities, 1:100, 2:100k, 3:10k, 4:1k, 5:1M, 6:250k, 7:500k 

def test(dataset_path, n):
    times = [] # [0] : add, [1] : box search, [2] : range search, [3] : knn search, [4] : erase

    print(f"\n📂 Testing dataset: {os.path.basename(dataset_path)}")
    fixed = FixedRecord("demo_file")

    # ADDING RECORDS
    print("📝 Adding records...")
    start_time = time.time()
    with open(dataset_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cc = 0
            for row in reader:
                if cc > n:
                    break
                reg = Registro(
                    id=int(row["id"]),
                    name=row["name"],
                    state_id=int(row["state_id"]),
                    state_code=row["state_code"],
                    state_name=row["state_name"],
                    country_id=int(row["country_id"]),
                    country_code=row["country_code"],
                    country_name=row["country_name"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    wikiDataId=row["wikiDataId"]
                )
                fixed.add(reg)
                cc += 1
    insert_time = time.time() - start_time
    times.append(insert_time)

    all = fixed.load()
    print(f"Inserted {len(all)} in record file.")
    print(f"⏱ Insert time: {insert_time:.4f}s")

    # Run spatial queries
    print("\n🔍 Box search:")
    start_time = time.time()
    box_matches = fixed.box_search((30.0, 30.0), (70.0, 70.0))
    box_time = time.time() - start_time
    times.append(box_time)

    if not box_matches:
        print(f"Found None in box search")
    else:
        print(f"Found {len(box_matches)} in box search")
    print(f"⏱ Box Search time: {box_time:.6f}s")

    print("\n📍 Radius search:")
    start_time = time.time()
    radius_matches = fixed.radius_search((55.0, 55.0), 25.0)
    radius_time = time.time() - start_time
    times.append(radius_time)

    if not radius_matches:
        print(f"Found None in radius search")
    else:
        print(f"Found {len(radius_matches)} in radius search")
    print(f"⏱ Radius Search time: {radius_time:.6f}s")

    print("\n👥 KNN search:")
    start_time = time.time()
    neighbors = fixed.knn_search((67.5, 67.5), 100)
    knn_time = time.time() - start_time
    times.append(knn_time)
    if not neighbors:
        print(f"Found None in KNN search")
    else:    
        print(f"Found {len(neighbors)} in KNN search")
    print(f"⏱ KNN Search time: {knn_time:.6f}s")

    positions = list(range(len(all)))
    sample_pos = random.sample(positions, 100)

    # REMOVAL
    print("\n❌ Removing 100 random records...")
    start_time = time.time()
    for p in sample_pos:
        fixed.remove(p)

    erase_time = time.time() - start_time
    times.append(erase_time)

    erase_count = len(all) - len(fixed.load())

    print(f"Deleted {erase_count} records.")
    print(f"⏱ Erase time: {erase_time:.4f}s")

    return times

times_test = test(files[2], 30000)
print(f"Insertion: {times_test[0]} | Box search: {times_test[1]} | Radius search: {times_test[2]} | KNN sarch: {times_test[3]} | Deletions: {times_test[4]}")

# Exit cleanup
for ext in ["dat", "free.dat", "rtree.dat", "rtree.idx", "rtree.meta.dat"]:
    try: os.remove(f"demo_file.{ext}")
    except: pass