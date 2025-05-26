from registro import Registro
from sequential import SequentialFile
import csv
import os
import time
import random
from itertools import islice

# Cleaning
for ext in ["dat", "aux.dat"]:
    try: os.remove(f"demo_file.{ext}")
    except: pass

csv_path = os.path.join(os.path.dirname(__file__), '..', 'data')
csv_path = os.path.normpath(csv_path)

files = [os.path.join(csv_path, i) for i in os.listdir(csv_path)]
# 0: cities, 1:100, 2:100k, 3:10k, 4:1k, 5:1M, 6:250k, 7:500k 

def test(dataset_path, n):
    times = [] # [0] : add, [1] : search, [2] : range search, [3] : erase

    print(f"\n📂 Testing dataset: {os.path.basename(dataset_path)}")
    seq = SequentialFile('demo_file', key_attr='id')

    # ADDING RECORDS
    print("📝 Adding records...")
    start_time = time.time()
    with open(dataset_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        cc = 0
        for row in reader:
            if cc > n:
                break
            reg = Registro(
                id=int(row['id']),
                name=row['name'],
                state_id=int(row['state_id']),
                state_code=row['state_code'],
                state_name=row['state_name'],
                country_id=int(row['country_id']),
                country_code=row['country_code'],
                country_name=row['country_name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                wikiDataId=row['wikiDataId']
            )
            seq.add(reg)
            cc += 1

    insert_time = time.time() - start_time
    times.append(insert_time)

    _, count = seq._read_header()
    aux_count = seq._count_aux_registros()
    print(f"Inserted {count} in main file, {aux_count} in auxiliary space. Total = {count + aux_count}.")
    print(f"⏱ Insert time: {insert_time:.4f}s")

    all = seq._load_all()
    keys = list({reg.id for reg in all})
    sample_keys = random.sample(keys, 100)

    # SEARCH
    print("\n🔍 Searching 100 random records:")
    start_time = time.time()
    search_count = 0
    for k in sample_keys:
        if seq.search(k):
            search_count += 1

    search_time = time.time() - start_time
    times.append(search_time)

    print(f"Succesful searches : {search_count}")
    print(f"⏱ Search time: {search_time:.6f}s")

    # RANGE SEARCH
    print("\n👥 Range search between id=75 and id=200:")
    start_time = time.time()
    matches = seq.range_search(75, 200)

    range_time = time.time() - start_time
    times.append(range_time)

    print(f"Found {len(matches)} records in range")
    print(f"⏱ Range search time: {range_time:.6f}s")

    # DELETIONS
    print("\n❌ Removing 100 random records")
    start_time = time.time()
    erase_count = 0
    for k in sample_keys:
        if seq.erase(k):
            erase_count += 1
    
    erase_time = time.time() - start_time
    times.append(erase_time)

    print(f"Deleted {erase_count} records.")
    print(f"⏱ Erase time: {erase_time:.4f}s")
    
    return times

times_test = test(files[2], 30000)
print("\n ALL TIMES:")
print(f"Insertion: {times_test[0]} | Search: {times_test[1]} | Range search: {times_test[2]} | Deletion: {times_test[3]}")

# Cleaning exit
for ext in ["dat", "aux.dat"]:
    try: os.remove(f"demo_file.{ext}")
    except: pass