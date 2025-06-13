from extendible_hashing import HashIndex, Registro
import os

## Usar fb=2, D=2 para poder ver bien los splits, overflow y reconstrucción

# test create, close, reopen existing hash #
print("Creating...")
hash_index = HashIndex("hash_index.bin")
#hash_index.print_index()
#hash_index.print_data()
print("Creation complete!\n")

print("Reopening...")
hash_index_reopen = HashIndex("hash_index.bin")
#hash_index_reopen.loadcsv("../data/cities_100.csv")
hash_index_reopen.print_index()
hash_index_reopen.print_data()
print("Reopen complete!\n")

# TEST insert, split and overflow"
regs = [Registro(2, "a", 1234, "ddd", "sfsdf", 1, "AF", "Afghanistan", 36.68333, 71.53333,"Q4805192"),
        Registro(1, "b", 3901, "BDS", "Badakhshan", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
        Registro(8, "c", 3901, "BDS", "Badakhshan", 1, "AF", "Afghanistan", 36.68333, 71.53333,"Q4805192"),
        Registro(16, "d", 3901, "BDS", "Badakhshan", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
        Registro(32, "e", 3901, "BDS", "Badakhshan", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
        Registro(3, "f", 1112, "BDS", "sloals", 1, "AF", "Afghanistan", 36.68333, 71.53333,"Q4805192"),
        Registro(5, "g", 1111, "BDS", "gaa", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
        Registro(9, "h", 3901, "BDS", "Badakhshan", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
        Registro(64, "i", 3901, "BDS", "Badakhshan", 1, "AF", "Afghanistan", 36.68333, 71.53333,"Q4805192"),
        Registro(128, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558")]

for reg in regs: 
    hash_index_reopen.insert(reg)
hash_index_reopen.print_data()
hash_index_reopen.print_index()

# test search, on regular and overflow buckets
search_keys = [3, 5, 128, 2, 9991]
for key in search_keys: 
    reg = hash_index_reopen.search(key)
    if reg == None: 
        print(f"No se encontró el registro con el key {key}")
    else: 
       reg.print_reg()

## Test remove and reconstruct ##
remove_keys = [2, 128, 32, 8, 9]
for key in remove_keys:
    hash_index_reopen.remove(key)

hash_index_reopen.print_data()
hash_index_reopen.print_index()


## Test insert after remove ## 
new_regs = [Registro(128, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
            Registro(7, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
            Registro(256, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
             Registro(512, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558")]
for reg in new_regs:
    hash_index_reopen.insert(reg)
hash_index_reopen.print_data()
hash_index_reopen.print_index()

#os.remove("data.bin")          
#os.remove("hash_index.bin")


## Test para la otra clase de registro ##
"""
#hago los mismos test pero ahora con la otra clase registro

index = HashIndex("hash_index.bin")

# TEST insert, split and overflow"
regs = [Registro(2,1),
        Registro(1,2),
        Registro(8,3),
        Registro(16),
        Registro(32),
        Registro(3),
        Registro(5),
        Registro(9),
        Registro(64),
        Registro(128)]

for reg in regs: 
    index.insert(reg)
index.print_data()
index.print_index()

# test search, on regular and overflow buckets
search_keys = [3, 5, 128, 2, 9991]
for key in search_keys: 
    reg = index.search(key)
    if reg == None: 
        print(f"No se encontró el registro con el key {key}")
    else: 
       reg.print_reg()

## Test remove and reconstruct ##
remove_keys = [2, 128, 32, 8, 9]
for key in remove_keys:
    index.remove(key)

index.print_data()
index.print_index()


## Test insert after remove ## 
new_regs = [Registro(128),
            Registro(7),
            Registro(256),
             Registro(512)]
for reg in new_regs:
    index.insert(reg)
index.print_data()
index.print_index()

#os.remove("data.bin")          
#os.remove("hash_index.bin")
"""