import struct
import os

REGISTER_FORMAT = 'i 60s i 5s 55s i 3s 35s f f 10s' 
RECORD_SIZE = struct.calcsize(REGISTER_FORMAT)

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
        self.wikiDataId.encode()
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
            unpacked[10].decode('utf-8', errors='replace').strip()  # wikiDataId
        )

    def print_reg(self):
        print(self.get_reg_string())

class FreeList:
    FORMAT = 'i'
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'wb'):
                pass
    
    def get_all(self):
        with open(self.filename, 'rb') as f:
            data = f.read()
            return [pos[0] for pos in struct.iter_unpack(self.FORMAT, data)]
    
    def add(self, pos):
        with open(self.filename, 'ab') as f:
            f.write(struct.pack(self.FORMAT, pos))
    
    def pop(self):
        positions = self.get_all()
        if not positions: 
            return None
        pos = positions.pop(0)
        
        with open(self.filename, 'wb') as f:
            for p in positions:
                f.write(struct.pack(self.FORMAT, p))
            
        return pos

class FixedRecord:
    def __init__(self, filename):
        self.filename = filename
        self.metadata = FreeList(filename + ".free")

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                pass

    def load(self):
        registros = []
        with open(self.filename, 'rb') as file:
            pos = 0
            while True:
                data = file.read(RECORD_SIZE)
                if not data or len(data) < RECORD_SIZE:
                    break
                registros.append((pos, Registro.from_bytes(data)))
                pos += 1

        free_positions = set(self.metadata.get_all())
        return [registro for i, registro in registros if i not in free_positions]

    def add(self, registro):
        pos = self.metadata.pop()
        with open(self.filename, 'r+b') as file:
            if pos is not None:
                file.seek(pos * RECORD_SIZE)
            else:
                file.seek(0, os.SEEK_END)
            file.write(registro.pack())

    def read(self, pos):
        with open(self.filename, 'rb') as file:
            file.seek(pos * RECORD_SIZE)
            data = file.read(RECORD_SIZE)
            if not data or len(data) < RECORD_SIZE:
                return None
            return Registro.from_bytes(data)

    def print_all(self):
        for reg in self.load():
            reg.print_reg()

    def remove(self, pos):
        self.metadata.add(pos)