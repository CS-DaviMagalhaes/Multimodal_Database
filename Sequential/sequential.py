import bisect
import math
import struct
import os
from registro import Registro

class SequentialFile:
    HEADER_FORMAT = 'i i' # first pos, count
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, filename, key_attr):
        self.filename = filename + ".dat"
        self.aux_filename = filename + ".aux.dat"
        self.key_attr = key_attr

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                file.write(struct.pack(self.HEADER_FORMAT, -1, 0))
    
    def _read_header(self):
        with open(self.filename, 'rb') as file:
            data = file.read(self.HEADER_SIZE)
            return struct.unpack(self.HEADER_FORMAT, data)
    
    def _write_header(self, start_pos, count):
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            file.write(struct.pack(self.HEADER_FORMAT, start_pos, count))

    def _count_aux_registros(self):
        size = os.path.getsize(self.aux_filename)
        return size // Registro.SIZE

    def _load_all(self):
        head, _ = self._read_header()
        registros = []

        with open(self.filename, 'rb') as file:
            current = head
            while current != -1:
                file.seek(self.HEADER_SIZE + current * (Registro.SIZE + 4))
                data = file.read(Registro.SIZE + 4)
                if not data or len(data) < (Registro.SIZE + 4):
                    break
                reg = Registro.from_bytes(data[:-4])
                next_ptr = struct.unpack('i', data[-4:])[0]
                registros.append(reg)
                current = next_ptr
        
        with open(self.aux_filename, 'rb') as file:
            while True:
                data = file.read(Registro.SIZE)
                if not data or len(data) < Registro.SIZE:
                    break
                registros.append(Registro.from_bytes(data))

        return registros

    def rebuild(self):
        all_registros = self._load_all()
        all_registros.sort(key = lambda r : getattr(r, self.key_attr))

        with open(self.filename, 'wb') as file:
            file.write(struct.pack(self.HEADER_FORMAT, 0, len(all_registros)))
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
                file.seek(self.HEADER_SIZE + current * (Registro.SIZE + 4))
                data = file.read(Registro.SIZE + 4)
                if not data or len(data) < (Registro.SIZE + 4):
                    break
            
                reg = Registro.from_bytes(data[:-4])
                next_ptr = struct.unpack('i', data[-4:])[0]

                if getattr(reg, self.key_attr) == key:
                    if prev is None:
                        self._write_header(next_ptr, count - 1)
                    else:
                        file.seek(self.HEADER_SIZE + prev * (Registro.SIZE + 4) + (Registro.SIZE))
                        file.write(struct.pack('i', next_ptr))
                        self._write_header(head, count - 1)
                    return True
            
                prev = current
                current = next_ptr
        
        return False