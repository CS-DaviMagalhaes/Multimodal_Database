from record import FixedRecord
from registro import Registro
import csv
import os
import time
import random



csv_path = os.path.join(os.path.dirname(__file__), '..', 'data')
csv_path = os.path.normpath(csv_path)

files = [os.path.join(csv_path, i) for i in os.listdir(csv_path)]
# 0: cities, 1:100, 2:100k, 3:10k, 4:1k, 5:1M, 6:250k, 7:500k 

def test(dataset_path):
    # Start cleanup
    for ext in ["dat", "free.dat", "rtree.dat", "rtree.idx", "rtree.meta.dat"]:
        try: os.remove(f"demo_file.{ext}")
        except: pass

    times = [] # [0] : add, [1] : search, [2] : range search, [3] : erase

    print(f"\n📂 Testing dataset: {os.path.basename(dataset_path)}")
    fixed = FixedRecord("demo_file")

    # ADDING RECORDS
    print("📝 Adding records...")
    start_time = time.time()
    with open(dataset_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            print("📝 Adding records...")
            for row in reader:
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
    insert_time = time.time() - start_time
    times.append(insert_time)

    all = fixed.load()
    print(f"Inserted {len(all)} in record file.")
    print(f"⏱ Insert time: {insert_time:.4f}s")

    # Run spatial queries
    print("\n🔍 Box search:")
    start_time = time.time()
    box_matches = fixed.box_search((0.0, 0.0), (1.0, 1.0))
    box_time = time.time() - start_time
    times.append(box_time)
    print(f"Found {len(box_matches)} in box search")
    print(f"⏱ Box Search time: {box_time:.6f}s")

    print("\n📍 Radius search:")
    start_time = time.time()
    radius_matches = fixed.radius_search((0.0, 0.0), 1.5)
    radius_time = time.time() - start_time
    times.append(radius_time)
    print(f"Found {len(radius_matches)} in radius search")
    print(f"⏱ Radius Search time: {radius_time:.6f}s")

    print("\n👥 KNN search:")
    start_time = time.time()
    neighbors = fixed.knn_search((0.25, 0.25), 3)
    knn_time = time.time() - start_time
    times.append(knn_time)
    print(f"Found {len(neighbors)} in KNN search")
    print(f"⏱ KNN Search time: {knn_time:.6f}s")

    keys = list(reg.id for reg in all)
    sample_keys = random.sample(keys, 100)

    # REMOVAL
    print("\n❌ Removing 100 random records...")
    start_time = time.time()
    for k in sample_keys:
        fixed.remove(k)

    erase_time = time.time() - start_time
    times.append(erase_time)

    erase_count = len(fixed.load()) - len(all)

    print(f"Deleted {erase_count} records.")
    print(f"⏱ Erase time: {erase_time:.4f}s")

    return times

times_test = files[4]
print(f"Insertion: {times_test[0]} | Search: {times_test[1]} | Range search: {times_test[2]} | Deletion: {times_test[3]}")

# Start cleanup
for ext in ["dat", "free.dat", "rtree.dat", "rtree.idx", "rtree.meta.dat"]:
    try: os.remove(f"demo_file.{ext}")
    except: pass