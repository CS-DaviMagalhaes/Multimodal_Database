import struct

REGISTER_FORMAT = 'ii' 
RECORD_SIZE = struct.calcsize(REGISTER_FORMAT) 
class Registro: 
    def __init__(self, id=0, pos=0):
        self.id = id
        self.pos = pos       

    def get_reg_string(self): 
        return " | ".join(str(v) for v in vars(self).values()) 
    

    def to_fields(self): #Encodifica todos los campos, asi puedo usar * 
        return (
            self.id,
            self.pos
        )
    
    @classmethod  #truquito que vi para poder leer todo de una vez a una clase -> reg = Registro.from_bytes(data)
    def from_bytes(cls, byte_data):
        unpacked = struct.unpack(REGISTER_FORMAT, byte_data)
        return cls(
            unpacked[0],
            unpacked[1]
        )

    def print_reg(self):
        print(self.get_reg_string())
