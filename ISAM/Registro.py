import struct

FORMAT = 'i 60s i 5s 55s i 3s 35s f f 10s' 
RECORD_SIZE = struct.calcsize(FORMAT)
BLOCK_FACTOR_DATA = 5
BLOCK_FACTOR_INDEX = 4
INDEX_ENTRY_SIZE = struct.calcsize('ii')  # id (int) + page_pos (int)

class Registro: # Cities
    FORMAT = 'i 60s i 5s 55s i 3s 35s f f 10s' 
    SIZE = struct.calcsize(FORMAT)

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
        
    def to_fields(self):
        return (
            self.id,
            self.name.encode('utf-8').ljust(60, b'\x00'),
            self.state_id,
            self.state_code.encode('utf-8').ljust(5, b'\x00'),
            self.state_name.encode('utf-8').ljust(55, b'\x00'),
            self.country_id,
            self.country_code.encode('utf-8').ljust(3, b'\x00'),
            self.country_name.encode('utf-8').ljust(35, b'\x00'),
            float(self.latitude),
            float(self.longitude),
            self.wikiDataId.encode('utf-8').ljust(10, b'\x00')
        )

    def pack(self):
        return struct.pack(
            self.FORMAT,
            *self.to_fields()
        )

    @classmethod  #truquito que vi para poder leer todo de una vez a una clase -> reg = Registro.from_bytes(data)
    def from_bytes(cls, byte_data):
        unpacked = struct.unpack(Registro.FORMAT, byte_data)
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

class IndexEntry:
    def __init__(self, key, page_pos):
        self.key = int(key)
        self.page_pos = int(page_pos)

    def pack(self):
        return struct.pack('ii', self.key, self.page_pos)

    @staticmethod
    def unpack(data):
        if len(data) < INDEX_ENTRY_SIZE:
            return None
        try:
            key, page_pos = struct.unpack('ii', data)
            return IndexEntry(key, page_pos)
        except Exception:
            return None