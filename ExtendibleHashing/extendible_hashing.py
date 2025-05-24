from cities import Registro, REGISTER_FORMAT, RECORD_SIZE
from struct import pack, unpack, calcsize
import os
import csv

fb = 2  # Factor de balanceo, cantidad maxima de elementos en un bucket
D = 2   # Profundidad global maxima

BUCKET_HEADER_FORMAT = 'iiii'
BUCKET_HEADER_SIZE = calcsize(BUCKET_HEADER_FORMAT)
BUCKET_FORMAT= f'iiii{fb*REGISTER_FORMAT}' # Bucket number, depth, next, size, fb espacios/registros
BUCKET_SIZE = calcsize(BUCKET_FORMAT) 

INDEX_FORMAT = f'{D}si' # String de longitud D y numero de bucket
INDEX_SIZE = calcsize(INDEX_FORMAT)


"""
Estructura: Reservo fb espacios por buckets, almaceno la cantidad de elementos reales. 
Bucket 0, d=1, next=-1, size=0
| 0
|
|
Bucket 1, d=1, next=-1, size=2
| 1
| 7
|
"""
class Bucket: 
    
    def __init__(self, bucket_id, d, items=[Registro() for _ in range(fb)]): #Por defecto fb registros "en blanco" para reservar espacio
        self.bucket_id = bucket_id  # ID del bucket, en decimal
        self.d = d                  # Profundidad local, para saber si puedo splitear o ya no
        self.next = -1              # Siguiente bucket enlazado
        self.size = 0               # Cantidad de elementos reales en el bucket 
        self.items = items          # Crear fb registros vacios (reservar espacio)

    def print_bucket(self): #Imprime el header y los registros no vacíos de un bucket
        print(f"Bucket {self.bucket_id} d={self.d} next={self.next} size={self.size}")
        for reg in self.items:
            if reg != Registro():
                reg.print_reg()

    
"""
Estrategia: Traigo el índice a RAM como un hash map para más eficiencia en las operaciones,
los buckets se quedan en memoria secundaria.

HashIndex.bin
Binary  | #Bucket
00           0
1            1
010          2
110          3
"""
class HashIndex:
    def __init__(self, index_filename="hash_index.bin", buckets_filename="data.bin"):
        self.index_filename = index_filename
        self.buckets_filename = buckets_filename
        self.index = {} # Hash index, mientras estoy trabajando sobre ello queda en ram

        if not os.path.exists(index_filename): 
            with open(index_filename,  "wb") as index_file: # Creo archivo index si no existe
                index_file.write(pack(INDEX_FORMAT, '0'.encode(), 0)) # Índice 0 (binary=0, #bucket 0)
                index_file.write(pack(INDEX_FORMAT, '1'.encode(), 1)) # Índice 1 (binary=1, #bucket 1)
            
            self.index["0"] = 0 
            self.index["1"] = 1
                
            with open(buckets_filename, "ab") as bucket_file: # Creo archivo bucket e inserto buckets iniciales
                self.add_empty_bucket(bucket_file, 0, 1)
                self.add_empty_bucket(bucket_file, 1, 1)
                
        else: 
            #Abrir índice existente
            with open(index_filename, "rb") as index_file: 
                while True:
                    data = index_file.read(INDEX_SIZE)
                    
                    if not data: # fin del archivo
                        break
                    
                    binary, number = unpack(INDEX_FORMAT, data)
                    self.index[binary.decode().rstrip('\x00')] = number 

    def get_bucket_header(self, bucket_file, bucket_number): # Retorna el header del bucket de numero bucket_number
        bucket_file.seek(bucket_number * BUCKET_SIZE)
        return unpack(BUCKET_HEADER_FORMAT, bucket_file.read(BUCKET_HEADER_SIZE)) # bucket_id, d, next_bucket, bucket_size

    def add_empty_bucket(self, bucket_file, bucket_number, d):
        bucket_file.seek(0,2) # End of file
        b = Bucket(bucket_number, d)
        all_fields = []
        for reg in b.items: # Reservar espacio para fb elementos (inserto registros vacios inicialmente)
            all_fields.extend(reg.to_fields())
        bucket_file.write(pack(BUCKET_FORMAT, b.bucket_id, b.d, b.next, b.size, *all_fields))
        
    def get_last_bucket_number(self, bucket_file): # Retorna el número del último bucket (para poder crear el siguiente)
        bucket_file.seek(-BUCKET_SIZE, 2)
        header_data = bucket_file.read(calcsize("iiii"))
        last_bucket_id, _, __, ___ = unpack("iiii", header_data)
        return last_bucket_id

    def get_bucket_items(self, bucket_file, bucket_number): # Usado para split
        #_, __, ___, bucket_size = self.get_bucket_header(bucket_file, bucket_number) #ver # de items en el bucket
        
        start_pos = calcsize("iiii") + bucket_number * BUCKET_SIZE # Posición del primer registro del bucket
        bucket_items = []
        for i in range(fb): # Itero sobre los elementos del bucket
            bucket_file.seek(start_pos + i*RECORD_SIZE) # Registro i del bucket
            data = bucket_file.read(RECORD_SIZE)

            if not data: 
                return None # No se encontró el registro
            
            reg = Registro.from_bytes(data) # Desempaqueto y creo un objeto registro con el contenido
            
            if reg != Registro(): # Saltar registros en blanco (borrados o vacios)
                bucket_items.append(reg)

        return bucket_items

    def reset_bucket(self, bucket_file, bucket_number): # Resetea los contenidos del bucket (para split) 
        #_, __, ___, bucket_size = self.get_bucket_header(bucket_file, bucket_number)

        start_pos = BUCKET_HEADER_SIZE + bucket_number * BUCKET_SIZE # Posición del primer registro del bucket
        for i in range(fb):
            bucket_file.seek(start_pos + i*RECORD_SIZE) # Registro i del bucket
            empty_reg = Registro()
            bucket_file.write(pack(REGISTER_FORMAT, *empty_reg.to_fields()))

        # Reseteo size
        bucket_file.seek(calcsize("iii") + bucket_number * BUCKET_SIZE) 
        bucket_file.write(pack("i", 0))       

    def insert(self, reg):  
        to_insert = [reg]
        while to_insert:
            reg = to_insert.pop(0)
            binary_id = bin(int(reg.id) % (2**D))[2:].zfill(D)
            
            bucket_number = 0 
            bucket_binary = binary_id
            for i in range(D):
                suffix = binary_id[i:]
                if suffix in self.index:
                    bucket_number = self.index[suffix]
                    bucket_binary = suffix
                    break       

            with open(self.buckets_filename, "r+b") as bucket_file:
                bucket_id, d, next_bucket, bucket_size = self.get_bucket_header(bucket_file, bucket_number)

                if bucket_size < fb: # Hay espacio, inserto
                    # Actualizo size en el header
                    bucket_file.seek(calcsize("iii") + bucket_number * BUCKET_SIZE)
                    bucket_file.write(pack("i", bucket_size + 1))

                    # Escribo registro
                    #TODO: change here, not bucket_size, iterate untill you find an empty spot, insert there.
                    pos = BUCKET_HEADER_SIZE + (bucket_size * RECORD_SIZE) + (bucket_number * BUCKET_SIZE)
                    bucket_file.seek(pos)
                    bucket_file.write(pack(REGISTER_FORMAT, *reg.to_fields()))
                    continue  # próximo en to_insert

                else:
                    #Verifico next hasta encontrar bucket con espacio
                    while next_bucket != -1:
                        bucket_file.seek(next_bucket * BUCKET_SIZE)
                        header_data = bucket_file.read(calcsize("iiii"))
                        bucket_number, d, next_bucket, bucket_size = unpack("iiii", header_data)

                    if bucket_size < fb:
                        bucket_file.seek(calcsize("iii") + bucket_number * BUCKET_SIZE)
                        bucket_file.write(pack("i", bucket_size + 1))
                        pos = calcsize("iiii") + (bucket_size * RECORD_SIZE) + (bucket_number * BUCKET_SIZE)
                        bucket_file.seek(pos)
                        bucket_file.write(pack(REGISTER_FORMAT, *reg.to_fields()))
                        continue

                    if d < D:  # Split
                        last_bucket_id = self.get_last_bucket_number(bucket_file)

                        if bucket_binary in self.index:
                            self.index.pop(bucket_binary)
                        bins = ("0" + bucket_binary, "1" + bucket_binary)
                        self.index[bins[0]] = bucket_id
                        self.index[bins[1]] = last_bucket_id + 1

                        # Actualizar archivo índice
                        with open(self.index_filename, "wb") as index_file:
                            index_file.seek(bucket_id * INDEX_SIZE)
                            index_file.write(pack(INDEX_FORMAT, bins[0].encode(), bucket_id))
                        with open(self.index_filename, "ab") as index_file:
                            index_file.write(pack(INDEX_FORMAT, bins[1].encode(), last_bucket_id + 1))

                        # Añadir nuevo bucket al final
                        self.add_empty_bucket(bucket_file, last_bucket_id+1, d+1)

                        # Redistribuir registros
                        items = self.get_bucket_items(bucket_file, bucket_id)
                        self.reset_bucket(bucket_file, bucket_id)
                        bucket_file.seek(calcsize("i") + bucket_number * BUCKET_SIZE)
                        bucket_file.write(pack("i", d + 1))

                        # Vuelvo a insertar los registros afectados
                        to_insert.extend(items + [reg])  # reinserto todos, incluido el original
                    
                    else: # d == D, encadeno buckets

                        # Creo bucket nuevo al final del archivo
                        last_bucket_id = self.get_last_bucket_number(bucket_file)
                        self.add_empty_bucket(bucket_file, last_bucket_id+1, d) #d==D

                        # Actualizar next del bucket "padre"
                        bucket_file.seek(calcsize("ii") + bucket_id * BUCKET_SIZE) #posición next del header del bucket
                        bucket_file.write(pack("i", last_bucket_id+1))
                        
                        # Escribir nuevo registro
                        bucket_file.seek(-BUCKET_SIZE+BUCKET_HEADER_SIZE, 2)
                        bucket_file.write(pack(REGISTER_FORMAT, *reg.to_fields()))
                        # Actualizar size del bucket con overflow
                        bucket_file.seek(-BUCKET_SIZE+calcsize("iii"), 2)
                        bucket_file.write(pack("i",1))
        
    def search(self, key):
        binary_id = bin(int(key) % (2**D))[2:].zfill(D)

        bucket_number = 0
        for i in range(D): # Buscar sufijo existente del bucket: 0100->100->00->0
            suffix = binary_id[i:]
            if suffix in self.index:
                bucket_number = self.index[suffix]
                break

        with open(self.buckets_filename, "rb") as bucket_file:
            while True:                 
                start_pos = calcsize("iiii") + bucket_number * BUCKET_SIZE # Posición del primer registro del bucket
                for i in range(fb): 
                    pos = start_pos + i*RECORD_SIZE
                    bucket_file.seek(pos) # Registro i del bucket
                    data = bucket_file.read(RECORD_SIZE)

                    if not data: 
                        return None, None # No se encontró el registro
                    
                    id, name, state_id, state_code, state_name, country_id, country_code, country_name, latitude, longitude, wikiDataId = unpack(REGISTER_FORMAT, data)

                    reg = Registro( id,
                                    name.decode(encoding='utf-8', errors='replace').strip(),
                                    state_id,
                                    state_code.decode().strip(),
                                    state_name.decode().strip(),
                                    country_id,
                                    country_code.decode().strip(),
                                    country_name.decode(encoding='utf-8', errors='replace').strip(),
                                    latitude,
                                    longitude,
                                    wikiDataId.decode(encoding='utf-8', errors='replace').strip())

                    if reg.id == key: 
                        return reg, pos # Retorno registro y posición del registro (para facilitar remove)
                    elif reg == Registro():
                        return None, None
                    
                # Voy al siguiente bucket linkeado
                bucket_file.seek(calcsize("ii") + bucket_number * BUCKET_SIZE) # Posición "next" del header del bucket
                
                next_bucket = unpack('i', bucket_file.read(calcsize('i')))[0] #Tomo solo el primer valor de la tupla, valor de next

                if next_bucket == -1: 
                    print(f"No existe registro con id {key}")
                    return None, None
                else: 
                    bucket_number = next_bucket # Voy al siguiente bucket par iterar sobre ello
                   
    def remove(self, key):
        reg, reg_pos = self.search(key)
        
        if reg == None: # No existe registro con ese key
            return
        
        with open(self.buckets_filename, "r+b") as bucket_file: 
            # Casos #
            # 1. Registro main, borro nomas, queda "en blanco"
            # 2. Registro en overflow
            #   2.1 borro y quedan registros
            #   2.2 borro y no quedan registros, overflow bucket vacio, lo dejo así nomas
            #       verificar si se imprimen los elementos bien si ese bucket vacio tiene otro de overflow adelante con elementos
            # 3. El % de buckets vacios > threshold, reconstrucción total


            bucket_file.seek(reg_pos)
            empty_reg = Registro()
            bucket_file.write(pack(REGISTER_FORMAT, *empty_reg.to_fields()))
            


            
    def print_index(self): # Imprimir el contenido del índice
        print(" -- Hash Index -- ")
        print(f"{'Binary':>8} | Bucket number")
        # Ordenar por el número de bucket (valor)
        for binary, bucket_number in sorted(self.index.items(), key=lambda x: x[1]):
            print(f'{binary:>8} | {bucket_number:>6}')
        print("----------------------------\n")

    def print_data(self): # Imprime todos los buckets, uno por uno
        print("-- Data.bin -- ")
        with open(self.buckets_filename, "rb") as bucket_file: 
            pos = 0
            while True:
                bucket_file.seek(pos * BUCKET_SIZE)
                bucket_header = bucket_file.read(calcsize("iiii")) # Leo header de ese bucket
                if not bucket_header: 
                    break   # ya se leyó todo

                bucket_id, d, next_bucket, bucket_size = unpack(BUCKET_HEADER_FORMAT, bucket_header) 
                
                bucket_items = []
                start_pos = BUCKET_HEADER_SIZE + pos * BUCKET_SIZE # Bucket actual + header -> primer registro
                for i in range(fb): 
                    bucket_file.seek(start_pos + i*RECORD_SIZE) # Registro i del bucket
                    data = bucket_file.read(RECORD_SIZE)

                    if len(data) < RECORD_SIZE:
                        return
    
                    reg = Registro.from_bytes(data) # Desempaqueto y creo un objeto registro con el contenido
                    bucket_items.append(reg)

                bucket = Bucket(bucket_id, d)
                bucket.next = next_bucket
                bucket.items = bucket_items
                bucket.size = bucket_size
                bucket.print_bucket()

                pos+=1
        print()      
    
    def loadcsv(self, csv_filename):
        with open(self.index_filename, "wb") as index_file:
            with open(csv_filename, newline='',encoding='ISO-8859-1') as csvfile:
                spamreader = csv.reader(csvfile, delimiter=',')
                next(spamreader, None)
                for row in spamreader: 
                    registro = Registro(int(row[0]),
                                        row[1],
                                        int(row[2]),
                                        row[3],
                                        row[4],
                                        int(row[5]),
                                        row[6],
                                        row[7],
                                        float(row[8]),
                                        float(row[9]),
                                        row[10])
                    
                    self.insert(registro)

####### TESTING #######

# test create, close, reopen existing hash #
print("Creating...")
hash_index = HashIndex("hash_index.bin")
#hash_index.print_index()
#hash_index.print_data()
print("Creation complete!\n")

print("Reopening...")
hash_index_reopen = HashIndex("hash_index.bin")
#hash_index_reopen.print_index()
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
search_keys = [3, 5, 128, 2]
for key in search_keys: 
    reg, pos = hash_index_reopen.search(key)
    if reg == None: 
        print(f"No se encontró el registro con el key {key}")
    else: 
       reg.print_reg()


#remove_keys = [2, 128]
#for key in remove_keys:
#    hash_index_reopen.remove(key)

#hash_index_reopen.print_data()

os.remove("data.bin")       #QUITAR esto. Es solo para poder testear rapido       
os.remove("hash_index.bin")