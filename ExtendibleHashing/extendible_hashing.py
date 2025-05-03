from ExtendibleHashing.registro import Registro, REGISTER_FORMAT, RECORD_SIZE
from struct import pack, unpack, calcsize
import sys
import os

D = 3
fb = 4 # Factor de balanceo, cantidad maxima de elementos en un bucket

BUCKET_FORMAT= f'iii{fb*REGISTER_FORMAT}' # Bucket number, depth, next, fb espacios/registros
BUCKET_SIZE = calcsize(BUCKET_FORMAT) 

INDEX_FORMAT = f'{D}si' # String de longitud D para binario y int para numero de bucket
INDEX_SIZE = calcsize(INDEX_FORMAT)


class Bucket: 
    def __init__(self, bucket_id, d, items=[Registro("", "", "", "", "") for _ in range(fb)]):
        self.d = d                  # Profundidad local
        self.bucket_id = bucket_id  # ID del bucket, en decimal
        self.next = -1              # Siguiente bucket enlazado
        self.items = items          # Crear fb registros vacios (reservar espacio)

        #Posición de un bucket (verificar): fb * (id+1), alocar fb espacios para cada 
        # Ejemplo quiero insertar en el bucket 2 --> fb=4*(2+1) = 12
        # Pos 1,2,3,4 registros bucket 0
        # pos 5,6,7,8 registros bucket 1
        # ... 

    def print_bucket(self):
        print(f"Bucket {self.bucket_id} d={self.d} next={self.next}")
        for reg in self.items:
            if reg.isbn != "":
                reg.print_reg()

    
"""
Estrategia: Traigo el índice a RAM como un hash map para más eficiencia en las operaciones

HashIndex.bin
Binary  | #Bucket
0            0
001          1
11           2
101          3
Almaceno el binary como un string ya que si lo almaceno como binario o entero no podré saber la longitud del binario
por ejemplo "001" me indica profundidad 3, sin embargo si lo almacenara como binario seria 0b1 o 1.
"""
class HashIndex:
    def __init__(self, index_filename="hash_index.bin", buckets_filename="data.bin"):
        self.index_filename = index_filename
        self.buckets_filename = buckets_filename
        self.values = {} # {"0": 1, "10": 2, ...}

        if not os.path.exists(index_filename): 
            with open(index_filename,  "wb") as index_file: # Creo archivo index si no existe
                index_file.write(pack(INDEX_FORMAT, "0".encode(), 0)) # Inicializar bucket 0 (id=0, depth=1)
                index_file.write(pack(INDEX_FORMAT, "1".encode(), 1)) 
                self.values["0"] = 0
                self.values["1"] = 1
                
            with open(buckets_filename, "wb") as bucket_file: # Creo archivo bucket e inserto buckets iniciales
                b0 = Bucket(0,1)
                all_fields = []
                for reg in b0.items: # Reservar espacio para fb elementos (inserto registros vacios inicialmente)
                    all_fields.extend(reg.to_fields())
                bucket_file.write(pack(BUCKET_FORMAT, b0.bucket_id, b0.d, b0.next, *all_fields))

                b1 = Bucket(1,1)
                all_fields = []
                for reg in b1.items:
                    all_fields.extend(reg.to_fields())
                bucket_file.write(pack(BUCKET_FORMAT, b1.bucket_id, b1.d, b1.next, *all_fields))
                

        else: 
            #Abrir índice existente
            with open(index_filename, "rb") as index_file: 
                while True:
                    data = index_file.read(INDEX_SIZE)
                    
                    if not data: # fin del archivo
                        break
                    
                    binary, number = unpack(INDEX_FORMAT, data)
                    self.values[binary.decode().strip()] = number 

    def insert(self, reg):
        
        #update index file in dict and file itself if split
        pass

    def search(self):
        pass

    def remove(self):
        pass
            
    def print_index(self): # Imprimir el contenido del índice
        print(f"{"Binary":>8} | Bucket number")
        for binary, bucket_number in self.values.items():
            print(f'{binary:>8} | {bucket_number:>6}')

    def print_data(self): # Imprime todos los buckets, uno por uno
        #reservar espacio de un solo bucket para la lectura, 
        with open(self.buckets_filename, "rb") as bucket_file: 
            while True:
                data = bucket_file.read(BUCKET_SIZE)

                if not data: 
                    break   # ya se leyó todo

                unpacked_data = unpack(BUCKET_FORMAT, data) #Tupla de valores
                
                bucket_id = unpacked_data[0]
                d = unpacked_data[1]
                next_bucket = unpacked_data[2]
                raw_fields = unpacked_data[3:]  # fb * (#campos registro)

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
                bucket.print_bucket()


#Testing#
hash_index = HashIndex("hash_index.bin")
hash_index.print_index()
hash_index.print_data()
#os.remove("data.bin")
#os.remove("hash_index.bin")
                
            

            
        
        
        
    