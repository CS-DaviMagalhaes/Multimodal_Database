import struct
"""
Longitudes máximas de los campos del dataset: 
Max length in 'id': 6               -> int
Max length in 'name': 59            -> string con caracteries ascii difetentes
Max length in 'state_id': 4         -> int
Max length in 'state_code': 5       -> string
Max length in 'state_name': 52      -> int
Max length in 'country_id': 3       -> string
Max length in 'country_code': 3     -> string
Max length in 'country_name': 32    -> string
Max length in 'latitude': 12        -> float
Max length in 'longitude': 13       -> float
Max length in 'wikiDataId': 10      -> string


Ejemplo
    id       name  state_id state_code  state_name  country_id country_code country_name  latitude  longitude wikiDataId
0   52  Ashkāsham      3901        BDS  Badakhshan           1           AF  Afghanistan  36.68333   71.53333   Q4805192
1   68   Fayzabad       3901        BDS  Badakhshan            1           AF  Afghanistan  37.11664   70.58002    Q156558
2   78       Jurm       3901        BDS  Badakhshan            1           AF  Afghanistan  36.86477   70.83421    Q10308323
3   84    Khandūd      3901        BDS  Badakhshan           1           AF  Afghanistan  36.95127   72.31800   Q3290334
4  115  Rāghistān      3901        BDS  Badakhshan           1           AF  Afghanistan  37.66079   70.67346   Q2670909
"""


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


# LECTURA #
"""
def from_binary(self, data):
    tokens, sizes = self.get_field_sizes(REGISTER_FORMAT)
    unpacked = struct.unpack(REGISTER_FORMAT, data)
    values = []

    for val, token in zip(unpacked, tokens):
        if token.endswith('s'):
            values.append(val.decode().strip())
        else:
            values.append(val)
    
    return Registro(*values)
"""


