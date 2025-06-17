import math
import struct
import os
from registro import Registro

class SequentialFile:
    HEADER_FORMAT = 'i' # count
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    REG_FORMAT = Registro.get_format()
    REG_SIZE = struct.calcsize(REG_FORMAT)

    def __init__(self, filename, key_attr):
        self.filename = filename + ".dat"
        self.aux_filename = filename + ".aux.dat"
        self.key_attr = key_attr

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                file.write(struct.pack(self.HEADER_FORMAT, 0))
    
    def _read_header(self):
        with open(self.filename, 'rb') as file:
            data = file.read(self.HEADER_SIZE)
            return struct.unpack(self.HEADER_FORMAT, data)[0]
    
    def _write_header(self, count):
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            file.write(struct.pack(self.HEADER_FORMAT, count))

    def _count_aux_registros(self):
        size = os.path.getsize(self.aux_filename)
        return size // self.REG_SIZE

    def _load_all(self):
        main_regs = []
        count = self._read_header()
        with open(self.filename, 'rb') as file:
            file.seek(self.HEADER_SIZE)
            for i in range(count):
                data = file.read(self.REG_SIZE + 1)
                if not data or len(data) < (self.REG_SIZE + 1):
                    break
                reg = Registro.from_bytes(data[:self.REG_SIZE])
                deleted = struct.unpack('B', data[self.REG_SIZE:])[0]
                if deleted == 0:
                    main_regs.append(reg)
        
        aux_regs = []
        with open(self.aux_filename, 'rb') as aux_file:
            while True:
                data = aux_file.read(self.REG_SIZE)
                if not data or len(data) < self.REG_SIZE:
                    break
                aux_regs.append(Registro.from_bytes(data))
        
        all_registros = main_regs + aux_regs
        return all_registros

    def rebuild(self):
        all_registros = self._load_all()
        all_registros.sort(key=lambda r: getattr(r, self.key_attr))

        with open(self.filename, 'wb') as file:
            file.write(struct.pack('i', len(all_registros)))
            
            for reg in all_registros:
                file.write(reg.pack())
                file.write(struct.pack('B', 0))
        
        open(self.aux_filename, 'wb').close()

    def add(self, registro):
        with open(self.aux_filename, 'ab') as aux_file:
            aux_file.write(registro.pack())
        
        count = self._read_header()
        if self._count_aux_registros() >= math.log2(count + 1):
            self.rebuild()
    
    def _binary_search(self, key):
        left = 0
        right = self._read_header() - 1

        with open(self.filename, 'r+b') as file:
            while left <= right:
                mid = (left + right) // 2
                offset = self.HEADER_SIZE + mid * (self.REG_SIZE + 1)
                file.seek(offset)
                data = file.read(self.REG_SIZE + 1)
                if len(data) < self.REG_SIZE + 1:
                    break
            
                reg = Registro.from_bytes(data[:self.REG_SIZE])
                reg_key = getattr(reg, self.key_attr)
                deleted = struct.unpack('B', data[self.REG_SIZE:])[0] 

                if reg_key == key:
                    if deleted == 0:
                        return reg, mid
                    else:
                        return None, -1
                elif reg_key < key:
                    left = mid + 1
                else:
                    right = mid - 1
        
        return None, -1

    def _lower_bound(self, key):
        left = 0
        right = self._read_header() - 1
        result_pos = None

        with open(self.filename, 'r+b') as file:
            while left <= right:
                mid = (left + right) // 2
                offset = self.HEADER_SIZE + mid * (self.REG_SIZE + 1)
                file.seek(offset)
                data = file.read(self.REG_SIZE + 1)
                if len(data) < self.REG_SIZE + 1:
                    break
            
                reg = Registro.from_bytes(data[:self.REG_SIZE])
                reg_key = getattr(reg, self.key_attr)

                if reg_key < key:
                    left = mid + 1
                else:
                    result_pos = mid
                    right = mid - 1
        
        return result_pos

    def search(self, key):
        matches = []
        count = self._read_header()
        pos = self._lower_bound(key)
            
        if pos is not None:
            with open(self.filename, 'rb') as file:
                i = pos
                
                # Si hay multiples registros con mismo key
                while i < count: 
                    offset = self.HEADER_SIZE + i * (self.REG_SIZE + 1)
                    file.seek(offset)
                    data = file.read(self.REG_SIZE + 1)
                    if len(data) < self.REG_SIZE + 1:
                        break

                    reg = Registro.from_bytes(data[:self.REG_SIZE])
                    reg_key = getattr(reg, self.key_attr)
                    deleted = struct.unpack('B', data[self.REG_SIZE:])[0]

                    # Matcheando
                    if reg_key == key and deleted == 0:
                        matches.append(reg)
                        i += 1
                    else:
                        break

        # Fallback: scanear el auxiliar
        with open(self.aux_filename, 'rb') as aux_file:
            while True:
                data = aux_file.read(self.REG_SIZE)
                if not data or len(data) < self.REG_SIZE:
                    break
                reg = Registro.from_bytes(data)
                reg_key = getattr(reg, self.key_attr)
                if reg_key == key:
                    matches.append(reg)

        return matches if matches else None

    def range_search(self, begin_key, end_key):
        matches = []
        count = self._read_header()
        pos = self._lower_bound(begin_key)

        if pos is None:
            pos = count

        with open(self.filename, 'rb') as file:
            i = pos
            while i < count:
                offset = self.HEADER_SIZE + i * (self.REG_SIZE + 1)
                file.seek(offset)
                data = file.read(self.REG_SIZE + 1)
                if len(data) < self.REG_SIZE + 1:
                    break

                reg = Registro.from_bytes(data[:self.REG_SIZE])
                reg_key = getattr(reg, self.key_attr)
                deleted = struct.unpack('B', data[self.REG_SIZE:])[0]

                if reg_key > end_key:
                    break

                if deleted == 0 and begin_key <= reg_key <= end_key:
                    matches.append(reg)

                i += 1

        # Fallback: scanear el auxiliar
        with open(self.aux_filename, 'rb') as aux_file:
            while True:
                data = aux_file.read(self.REG_SIZE)
                if not data or len(data) < self.REG_SIZE:
                    break
                reg = Registro.from_bytes(data)
                reg_key = getattr(reg, self.key_attr)
                if begin_key <= reg_key <= end_key:
                    matches.append(reg)

        return matches if matches else None

    def erase(self, key):
        count = self._read_header()
        erased = False
        pos = self._lower_bound(key)
        deleted_any = False

        if pos is None:
            return False
    
        with open(self.filename, 'r+b') as file:
            i = pos
            while i < count: # Buscamos mas de uno
                offset = self.HEADER_SIZE + i * (self.REG_SIZE + 1)
                file.seek(offset)
                data = file.read(self.REG_SIZE + 1)
                if len(data) < self.REG_SIZE + 1:
                    break

                reg = Registro.from_bytes(data[:self.REG_SIZE])
                reg_key = getattr(reg, self.key_attr)
                deleted = struct.unpack('B', data[self.REG_SIZE:])[0]

                if reg_key == key: # Borramos
                    if deleted == 0:
                        file.seek(offset + self.REG_SIZE)
                        file.write(b'\x01')
                        count -= 1
                        deleted_any = True
                    i += 1
                else:
                    break

        if deleted_any:
            self._write_header(count)

        return deleted_any