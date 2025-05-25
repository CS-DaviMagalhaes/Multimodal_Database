import struct
import os

class RTreeMetadata:
    """
    Resulta que la metadata de rtree no mantiene las coordenadas de cada 
    uno de los elementos. No quedade otra que manejarlo con un archivo de 
    metadata aparte que los que crea la librería.
    
    Archivo de metadata para el RTree. Manejado con un free list, mantiene 
    el id, posicion y coordenadas de cada registro dentro del RTree.
    """
    FORMAT = 'i i f f i'
    SIZE = struct.calcsize(FORMAT)
    HEADER_FORMAT = 'i'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, filename):
        self.filename = filename

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                file.write(struct.pack(self.HEADER_FORMAT, -1))
    
    def read_header(self):
        with open(self.filename, 'rb') as file:
            return struct.unpack(self.HEADER_FORMAT, file.read(self.HEADER_SIZE))[0]

    def write_header(self, head):
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            file.write(struct.pack(self.HEADER_FORMAT, head))
    
    def add(self, key, pos, lon, lat):
        head = self.read_header()
        if head == -1:
            with open(self.filename, 'ab') as file:
                entry = struct.pack(self.FORMAT, key, pos, lon, lat, -1)
                file.write(entry)
        else:
            with open(self.filename, 'r+b') as file:
                entry_offset = self.HEADER_SIZE + head * self.SIZE
                file.seek(entry_offset)
                _, _, _, _, next_free = struct.unpack(self.FORMAT, file.read(self.SIZE))
                file.seek(entry_offset)
                file.write(struct.pack(self.FORMAT, key, pos, lon, lat, -1))
                self.write_header(next_free)
    
    def get(self, key):
        with open(self.filename, 'rb') as file:
            file.seek(self.HEADER_SIZE)
            index = 0
            while True:
                bytes_read = file.read(self.SIZE)
                if not bytes_read or len(bytes_read) < self.SIZE:
                    break
                unpacked = struct.unpack(self.FORMAT, bytes_read)
                if unpacked[0] == key:
                    return {
                        'key': unpacked[0],
                        'pos': unpacked[1],
                        'lon': unpacked[2],
                        'lat': unpacked[3],
                        'offset': self.HEADER_SIZE + index * self.SIZE
                    }
                index += 1
        return None

    def erase(self, key):
        entry = self.get(key)
        if not entry:
            return False
        offset = entry['offset']
        free_head = self.read_header()
        with open(self.filename, 'r+b') as file:
            file.seek(offset)
            file.write(struct.pack(self.FORMAT, -1, -1, 0.0, 0.0, free_head))
        self.write_header((offset - self.HEADER_SIZE) // self.SIZE)
        return True