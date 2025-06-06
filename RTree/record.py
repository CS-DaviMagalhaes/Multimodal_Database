import struct
import os
from rtree_index import RTreeIndex
from registro import Registro

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
        self.filename = filename + ".dat"
        self.free_list = FreeList(filename + ".free.dat")
        self.index = RTreeIndex(index_name=filename + ".rtree")

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                pass

    def load(self):
        free_positions = set(self.free_list.get_all())
        registros = []
        with open(self.filename, 'rb') as file:
            pos = 0
            while True:
                data = file.read(Registro.SIZE)
                if not data or len(data) < Registro.SIZE:
                    break
                if pos not in free_positions:
                    registros.append((pos, Registro.from_bytes(data)))
                pos += 1

        return registros

    def add(self, registro):
        pos = self.free_list.pop()
        with open(self.filename, 'r+b') as file:
            if pos is not None:
                file.seek(pos * Registro.SIZE)
            else:
                file.seek(0, os.SEEK_END)
                pos = file.tell() // Registro.SIZE
            file.write(registro.pack())
        
        self.index.add(registro, pos)    
        return pos

    def read(self, pos):
        if pos in self.free_list.get_all():
            return None
        with open(self.filename, 'rb') as file:
            file.seek(pos * Registro.SIZE)
            data = file.read(Registro.SIZE)
            if not data or len(data) < Registro.SIZE:
                return None
            return Registro.from_bytes(data)

    def print_registros(self, regs):
        for reg in regs:
            reg.print_reg()

    def box_search(self, lower_coords, upper_coords):
        matches = self.index.box_search(lower_coords, upper_coords)

        if not matches:
            return None

        registros = [self.read(match) for match in matches]            
        return registros

    def radius_search(self, coords, radius):
        matches = self.index.radius_search(coords, radius)

        if not matches:
            return None

        registros = [self.read(match) for match in matches]
        return registros

    def knn_search(self, coords, k):
        matches = self.index.knn_search(coords, k)

        if not matches:
            return None

        registros = [self.read(match) for match in matches]
        return registros

    def remove(self, pos):
        self.index.erase(pos)
        self.free_list.add(pos)