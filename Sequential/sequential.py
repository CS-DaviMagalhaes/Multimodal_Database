import bisect
import math
import struct
import os

REGISTER_FORMAT = 'i 60s i 5s 55s i 3s 35s f f 10s' 
RECORD_SIZE = struct.calcsize(REGISTER_FORMAT)
HEADER_FORMAT = 'i i' # first pos, count
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

class Registro: # Cities
    def __init__(self, id=0, name="", state_id=0, state_code="", state_name="",
                 country_id=0, country_code="", country_name="", latitude=0.0,
                 longitude=0.0, wikiDataId=""): #para constructor "vacio"
        
        self.id = id                                        
        self.name = name                   
        self.state_id = state_id            
        self.state_code = state_code        
        self.state_name = state_name        
        self.country_id = country_id        
        self.country_code = country_code        
        self.country_name = country_name        
        self.latitude = latitude        
        self.longitude = longitude      
        self.wikiDataId = wikiDataId   

    def get_reg_string(self): # vars(self).values() retorna el valor de todas las variables de la clase
        return " | ".join(str(v) for v in vars(self).values()) # name | state_id | state_code | ...
        
    def to_fields(self): #Encodifica todos los campos, asi puedo usar * 
        return (
        self.id,
        self.name.encode(),
        self.state_id,
        self.state_code.encode(),
        self.state_name.encode(),
        self.country_id,
        self.country_code.encode(),
        self.country_name.encode(),
        self.latitude,
        self.longitude,
        self.wikiDataId.encode(),
    )

    def pack(self):
        return struct.pack(
            REGISTER_FORMAT,
            *self.to_fields()
        )

    @classmethod  #truquito que vi para poder leer todo de una vez a una clase -> reg = Registro.from_bytes(data)
    def from_bytes(cls, byte_data):
        unpacked = struct.unpack(REGISTER_FORMAT, byte_data)
        return cls(
            unpacked[0],  # id
            unpacked[1].decode('utf-8', errors='replace').strip(),  # name
            unpacked[2],  # state_id
            unpacked[3].decode().strip(),  # state_code
            unpacked[4].decode().strip(),  # state_name
            unpacked[5],  # country_id
            unpacked[6].decode().strip(),  # country_code
            unpacked[7].decode('utf-8', errors='replace').strip(),  # country_name
            unpacked[8],  # latitude
            unpacked[9],  # longitude
            unpacked[10].decode('utf-8', errors='replace').strip(),  # wikiDataId
        )

    def print_reg(self):
        print(self.get_reg_string())

class SequentialFile:
    def __init__(self, filename, key_attr):
        self.filename = filename + ".dat"
        self.aux_filename = filename + ".aux.dat"
        self.key_attr = key_attr

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                file.write(struct.pack(HEADER_FORMAT, -1, 0))
    
    def _read_header(self):
        with open(self.filename, 'rb') as file:
            data = file.read(HEADER_SIZE)
            return struct.unpack(HEADER_FORMAT, data)
    
    def _write_header(self, start_pos, count):
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            file.write(struct.pack(HEADER_FORMAT, start_pos, count))

    def _count_aux_registros(self):
        size = os.path.getsize(self.aux_filename)
        return size // RECORD_SIZE

    def _load_all(self):
        head, _ = self._read_header()
        registros = []

        with open(self.filename, 'rb') as file:
            current = head
            while current != -1:
                file.seek(HEADER_SIZE + current * (RECORD_SIZE + 4))
                data = file.read(RECORD_SIZE + 4)
                if not data or len(data) < (RECORD_SIZE + 4):
                    break
                reg = Registro.from_bytes(data[:-4])
                next_ptr = struct.unpack('i', data[-4:])[0]
                registros.append(reg)
                current = next_ptr
        
        with open(self.aux_filename, 'rb') as file:
            while True:
                data = file.read(RECORD_SIZE)
                if not data or len(data) < RECORD_SIZE:
                    break
                registros.append(Registro.from_bytes(data))

        return registros

    def rebuild(self):
        all_registros = self._load_all()
        all_registros.sort(key = lambda r : getattr(r, self.key_attr))

        with open(self.filename, 'wb') as file:
            file.write(struct.pack(HEADER_FORMAT, 0, len(all_registros)))
            for i, reg in enumerate(all_registros):
                file.write(reg.pack())
                next_ptr = i + 1 if i + 1 < len(all_registros) else -1
                file.write(struct.pack('i', next_ptr))
        
        open(self.aux_filename, 'wb').close()

    def add(self, registro):
        key = getattr(registro, self.key_attr)

        with open(self.aux_filename, 'ab') as aux_file:
            aux_file.write(registro.pack())
        
        _, count = self._read_header()
        if self._count_aux_registros() >= math.log2(count + 1):
            self.rebuild()
    
    def search(self, key):
        all_registros = self._load_all()
        all_registros.sort(key = lambda r: getattr(r, self.key_attr))

        keys = [getattr(r, self.key_attr) for r in all_registros]

        index = bisect.bisect_left(keys, key)
        if index < len(keys) and keys[index] == key:
            return all_registros[index]
        return None

    def range_search(self, begin_key, end_key):
        all_registros = self._load_all()
        all_registros.sort(key = lambda r : getattr(r, self.key_attr))

        keys = [getattr(r, self.key_attr) for r in all_registros]

        start_idx = bisect.bisect_left(keys, begin_key)
        end_idx = bisect.bisect_right(keys, end_key)
    
        return all_registros[start_idx:end_idx]

    def erase(self, key):
        head, count = self._read_header()
        prev = None
        current = head

        with open(self.filename, 'r+b') as file:
            while current != -1:
                file.seek(HEADER_SIZE + current * (RECORD_SIZE + 4))
                data = file.read(RECORD_SIZE + 4)
                if not data or len(data) < (RECORD_SIZE + 4):
                    break
            
                reg = Registro.from_bytes(data[:-4])
                next_ptr = struct.unpack('i', data[-4:])[0]

                if getattr(reg, self.key_attr) == key:
                    if prev is None:
                        self._write_header(next_ptr, count - 1)
                    else:
                        file.seek(HEADER_SIZE + prev * (RECORD_SIZE + 4) + (RECORD_SIZE))
                        file.write(struct.pack('i', next_ptr))
                        self._write_header(head, count - 1)
                    return True
            
                prev = current
                current = next_ptr
        
        return False