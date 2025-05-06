from registro import Registro, REGISTER_FORMAT, RECORD_SIZE
from struct import pack, unpack, calcsize
import sys
import os

fb = 4          # Factor de balanceo, cantidad maxima de elementos en un bucket
MAX_DEPTH = 3   # Profundidad global maxima

BUCKET_FORMAT= f'iiii{fb*REGISTER_FORMAT}' # Bucket number, depth, next, size, fb espacios/registros
BUCKET_SIZE = calcsize(BUCKET_FORMAT) 

INDEX_FORMAT = f'{MAX_DEPTH}si' # String de longitud MAX_DEPTH y numero de bucket
INDEX_SIZE = calcsize(INDEX_FORMAT)


"""
Estructura: Reservo fb espacios por buckets, almaceno la cantidad de elementos reales. 
Bucket 0, d=1, next=-1, size=0
|
|
|
Bucket 1, d=1, next=-1, size=2
| 1
| 7
|
"""

class Bucket: 
    def __init__(self, bucket_id, d, items=[Registro("A", "A", "A", "A", "A") for _ in range(fb)]):
        self.d = d                  # Profundidad local
        self.bucket_id = bucket_id  # ID del bucket, en decimal
        self.next = -1              # Siguiente bucket enlazado
        self.items = items          # Crear fb registros vacios (reservar espacio)
        self.size = 0               # Cantidad de elementos reales en el bucket 

    def print_bucket(self):
        print(f"Bucket {self.bucket_id} d={self.d} next={self.next} size={self.size}")
        for reg in self.items:
            if reg.isbn != "":
                reg.print_reg()

    
"""
Estrategia: Traigo el índice a RAM como un hash map para más eficiencia en las operaciones,
los buckets se quedan en memoria secundaria.

HashIndex.bin
Binary  | #Bucket
000         0
100         3     
001         1
010         2
"""
class HashIndex:
    def __init__(self, index_filename="hash_index.bin", buckets_filename="data.bin"):
        self.index_filename = index_filename
        self.buckets_filename = buckets_filename
        self.index = {} # Hash index, mientras estoy trabajando sobre ello queda en ram
        self.D = 1 # Profundidad global, aumenta conforme hago split

        if not os.path.exists(index_filename): 
            with open(index_filename,  "wb") as index_file: # Creo archivo index si no existe
                index_file.write(pack(INDEX_FORMAT, "0".encode(), 0)) # Índice 0 (binary=0, #bucket 0)
                index_file.write(pack(INDEX_FORMAT, "1".encode(), 1)) # Índice 1 (binary=1, #bucket 1)
            
            self.index["0"] = 0 
            self.index["1"] = 1
                
            #TODO: limpiar esta parte
            with open(buckets_filename, "wb") as bucket_file: # Creo archivo bucket e inserto buckets iniciales
                b0 = Bucket(0,1) # Bucket 0, d=1
                all_fields = []
                for reg in b0.items: # Reservar espacio para fb elementos (inserto registros vacios inicialmente)
                    all_fields.extend(reg.to_fields())
                bucket_file.write(pack(BUCKET_FORMAT, b0.bucket_id, b0.d, b0.next, b0.size, *all_fields))

                b1 = Bucket(1,1) # Bucket 1, d=1
                all_fields = []
                for reg in b1.items:
                    all_fields.extend(reg.to_fields())
                bucket_file.write(pack(BUCKET_FORMAT, b1.bucket_id, b1.d, b1.next, b1.size, *all_fields))
                
        else: 
            #Abrir índice existente
            with open(index_filename, "rb") as index_file: 
                while True:
                    data = index_file.read(INDEX_SIZE)
                    
                    if not data: # fin del archivo
                        break
                    
                    binary, number = unpack(INDEX_FORMAT, data)
                    print("bin ", len(binary.decode()))
                    self.index[binary.decode().rstrip('\x00')] = number #this is writing \x00 aaaa TODO FIX  

    def insert(self, reg):  
        bucket_binary = bin(int(reg.isbn) % (2^self.D))[2:]
        print(self.index)
        bucket_number  = self.index[bucket_binary]
        #TODO: verificar si existe realmente caso donde no se encuentra el numero de bucket

        with open(self.buckets_filename, "r+b") as bucket_file:

            #Encontrar el header del bucket
            bucket_file.seek(bucket_number * BUCKET_SIZE)
            data = bucket_file.read(calcsize("iiii"))
            unpacked_data = unpack("iiii", data)
                
            bucket_id = unpacked_data[0]
            d = unpacked_data[1]
            next_bucket = unpacked_data[2]
            bucket_size = unpacked_data[3]

            if bucket_size < fb: 
                # Hay espacio, inserto
                bucket_file.seek(calcsize("iii") + bucket_number * BUCKET_SIZE) # Posición "size" del header
                bucket_file.write(pack("i", bucket_size+1)) # Actualizo size

                bucket_file.seek(calcsize("iiii") + (bucket_size*RECORD_SIZE) + (bucket_number*BUCKET_SIZE)) # Posición especifica del bucket
                # Sobreescribo registro en blanco por registro real
                bucket_file.write(pack(REGISTER_FORMAT, 
                                  reg.isbn.encode(),
                                  reg.title.encode(),
                                  reg.year.encode(),
                                  reg.author.encode(),
                                  reg.publisher.encode()))              
            else: 
                #Verifico recursivamente next hasta encontrar bucket con espacio
                while next_bucket == -1:
                    #Encontrar el header del bucket
                    bucket_file.seek(next_bucket * BUCKET_SIZE)
                    data = bucket_file.read(calcsize("iiii"))
                    unpacked_data = unpack("iiii", data)
                        
                    bucket_id = unpacked_data[0]
                    d = unpacked_data[1]
                    next_bucket = unpacked_data[2]
                    bucket_size = unpacked_data[3]

                # Ya encontré el bucket, verifico si está lleno
                if bucket_size < fb: 
                                    # Hay espacio, inserto
                    bucket_file.seek(calcsize("iii") + bucket_number * BUCKET_SIZE) # Posición "size" del header
                    bucket_file.write(pack("i", bucket_size+1)) # Actualizo size

                    bucket_file.seek(calcsize("iiii") + (bucket_size*RECORD_SIZE) + (bucket_number*BUCKET_SIZE)) # Posición especifica del bucket
                    # Sobreescribo registro en blanco por registro real
                    bucket_file.write(pack(REGISTER_FORMAT, 
                                    reg.isbn.encode(),
                                    reg.title.encode(),
                                    reg.year.encode(),
                                    reg.author.encode(),
                                    reg.publisher.encode()))    
                else: 
                    # Overflow, hago split
                    #verifico cual es el ultimo bucket
                    #bucket_file.seek(0, 2 - cuatro regs, leer header, ver numero bucket, el nuevo split sera ese num mas 1)
                    pass
                    #bucket_file.seek(calcsize("ii") + bucket_number * BUCKET_SIZE) # Posición "next" del header
                    #bucket_file.write(pack("i", bucket_size+1)) # Actualizo size

                
          
    def search(self):
        pass

    def remove(self):
        pass
            
    def print_index(self): # Imprimir el contenido del índice
        print(" -- Hash Index -- ")
        print(f"{"Binary":>8} | Bucket number")
        for binary, bucket_number in self.index.items():
            print(f'{binary:>8} | {bucket_number:>6}')
        print("----------------------------\n")

    def print_data(self): # Imprime todos los buckets, uno por uno
        print("-- Data.bin -- ")
        with open(self.buckets_filename, "rb") as bucket_file: 
            while True:
                data = bucket_file.read(BUCKET_SIZE)

                if not data: 
                    break   # ya se leyó todo

                unpacked_data = unpack(BUCKET_FORMAT, data) #Tupla de valores
                
                bucket_id = unpacked_data[0]
                d = unpacked_data[1]
                next_bucket = unpacked_data[2]
                bucket_size = unpacked_data[3]
                raw_fields = unpacked_data[4:]  # fb * (#campos registro)

                items = []
                for i in range(fb):
                    base = i * 5
                    reg_fields = raw_fields[base:base + 5]
                    reg = Registro(
                        reg_fields[0].decode(), # isbn
                        reg_fields[1].decode(), # title
                        reg_fields[2].decode(), # author
                        reg_fields[3].decode(), # year
                        reg_fields[4].decode(), # publisher
                    )
                    items.append(reg)

                bucket = Bucket(bucket_id, d)
                bucket.next = next_bucket
                bucket.items = items
                bucket.size = bucket_size
                bucket.print_bucket()
        print()

#Testing#
print("Creating...")
hash_index = HashIndex("hash_index.bin")
hash_index.print_index()
hash_index.print_data()

print("Reopening...")
hash_index_reopen = HashIndex("hash_index.bin")
hash_index_reopen.print_index()
hash_index_reopen.print_data()


# Test insert # 
reg1 = Registro("195153448","Classical Mythology","Mark P. O. Morford","2002","Oxford University Press")
reg2 = Registro("2005018","Clara Callan","Richard Bruce Wright","2001","HarperFlamingo Canada")
hash_index_reopen.insert(reg1)
hash_index_reopen.insert(reg2)
hash_index_reopen.print_index()
hash_index_reopen.print_data()


os.remove("data.bin")
os.remove("hash_index.bin")

            

            
        
        
        
    