import struct
import os

class Record:
    FORMAT = "i20sdd"
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, id, name, lat, lon):
        self.id = id
        self.name = name
        self.lat = lat
        self.lon = lon
    
    def display(self):
        return f"[{self.id}] {self.name} : ( {self.lat} , {self.lon} )"

    def pack(self):
        return struct.pack(
            Record.FORMAT,
            self.id,
            self.name.encode(),
            self.lat,
            self.lon
        )

    @staticmethod
    def unpack(data):
        unpacked = struct.unpack(Record.FORMAT, data)
        return Record(
            unpacked[0],
            unpacked[1].decode().rstrip('\x00').strip(),
            unpacked[2],
            unpacked[3]
        )

class RecordFile:
    HEADER_SIZE = 4
    def __init__(self, filename):
        """
        Archivo almacén de records. Será la 
        base del índice creado con el RTree.
        Utiliza un header para la free list.
        """
        self.filename = filename

        if not os.path.exists(self.filename) or os.path.getsize(self.filename) < self.HEADER_SIZE:
            with open(self.filename, 'wb') as file:
                file.write(struct.pack('i'), -1)
    
    def _read_header(self):
        """
        Lee el header del archivo.
        """
        with open(self.filename, 'rb') as file:
            return struct.unpack('i', file.read(self.HEADER_SIZE))[0]
    
    def _write_header(self, value):
        """
        Sobreescribe el header del archivo.
        Util para actualizar la free list.
        """
        with open(self.filename, 'r+b') as file:
            file.write(struct.pack('i', value))
    
    def add(self, record):
        """
        Inserta un nuevo record al archivo.
        No interesa preservar el orden aquí.
        """
        pass

    def read(self, pos):
        """
        Lee un registro en cierta posición
        dentro del archivo
        """
        pass

    def search(self, key):
        """
        Búsqueda dentro del archivo. Se
        apoya en el método del RTree.
        """
        pass

    def range_search(self, begin_key, end_key):
        """
        Búsqueda de rango dentro del archivo.
        Se apoya en el método del RTree.
        """
        pass

    def remove(self, key):
        """
        Borra elementos usando el método dentro del RTree.
        """
        pass