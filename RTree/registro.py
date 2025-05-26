import struct

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
