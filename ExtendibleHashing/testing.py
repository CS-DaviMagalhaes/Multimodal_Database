from extendible_hashing import HashIndex
from cities import Registro, REGISTER_FORMAT, RECORD_SIZE
from struct import pack, unpack, calcsize
import os
import csv

# test create, close, reopen existing hash #
print("Creating...")
hash_index = HashIndex("hash_index.bin")
#hash_index.print_index()
#hash_index.print_data()
print("Creation complete!\n")

print("Reopening...")
hash_index_reopen = HashIndex("hash_index.bin")
#hash_index_reopen.loadcsv("../data/cities.csv")
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
search_keys = [3, 5, 128, 2, 0]
for key in search_keys: 
    reg = hash_index_reopen.search(key)
    if reg == None: 
        print(f"No se encontró el registro con el key {key}")
    else: 
       reg.print_reg()

## Test remove ##
remove_keys = [2,128, 32, 8, 9]
for key in remove_keys:
    hash_index_reopen.remove(key)

hash_index_reopen.print_data()
hash_index_reopen.print_index()


## Test insert after remove ## 
#new_regs = [Registro(128, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
#            Registro(7, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
#            Registro(256, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558"),
#             Registro(512, "j", 2222, "xdd", "asdfasdf", 1, "AF", "Afghanistan", 37.11664, 70.58002, "Q156558")]
#for reg in new_regs:
#    hash_index_reopen.insert(reg)
#hash_index_reopen.print_data()


os.remove("data.bin")       #QUITAR esto. Es solo para poder testear rapido       
os.remove("hash_index.bin")
