import math
import struct
import os

class SequentialFile:
    HEADER_FORMAT = 'i' # count
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    def __init__(self, filename, key_attr, key_type):
        self.filename = filename + ".seq"
        self.aux_filename = filename + ".seq.aux"
        self.key_attr = key_attr
        self.key_type = key_type

        self._set_index_entry_format()

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                file.write(struct.pack(self.HEADER_FORMAT, 0))
    
    def _set_index_entry_format(self):
        if self.key_type == "int":
            self.ENTRY_KEY_FORMAT = 'i'
        elif self.key_type.startswith("varchar"):
            size = int(self.key_type[self.key_type.find("(")+1:self.key_type.find(")")])
            self.ENTRY_KEY_FORMAT = f"{size}s"
        else:
            raise ValueError(f"Tipo {self.key_type} para llaves no soportado para Sequential File.")

        self.ENTRY_FORMAT = f'{self.ENTRY_KEY_FORMAT} i B'
        self.ENTRY_SIZE = struct.calcsize(self.ENTRY_FORMAT)

    def _read_header(self):
        with open(self.filename, 'rb') as file:
            data = file.read(self.HEADER_SIZE)
            return struct.unpack(self.HEADER_FORMAT, data)[0]
    
    def _write_header(self, count):
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            file.write(struct.pack(self.HEADER_FORMAT, count))

    def _count_aux_entries(self):
        if not os.path.exists(self.aux_filename):
            return 0
        size = os.path.getsize(self.aux_filename)
        return size // self.ENTRY_SIZE if self.ENTRY_SIZE else 0

    def _load_all(self):
        all_entries = []
        count = self._read_header()
        
        with open(self.filename, 'rb') as file:
            file.seek(self.HEADER_SIZE)
            for i in range(count):
                data = file.read(self.ENTRY_SIZE)
                if not data or len(data) < self.ENTRY_SIZE:
                    break

                unpacked = struct.unpack(self.ENTRY_FORMAT, data)
                key_value = unpacked[0]
                record_pos = unpacked[1]
                deleted_flag = unpacked[2]

                if deleted_flag == 0:
                    if self.key_type.startswith("varchar"):
                        key_value = key_value.decode('utf-8').strip()
                    all_entries.append((key_value, record_pos))

        if os.path.exists(self.aux_filename):
            with open(self.aux_filename, 'rb') as aux_file:
                while True:
                    data = aux_file.read(self.ENTRY_SIZE)
                    if not data or len(data) < self.ENTRY_SIZE:
                        break
                    
                    unpacked = struct.unpack(self.ENTRY_FORMAT, data)
                    key_value = unpacked[0]
                    record_pos = unpacked[1]
                    deleted_flag = unpacked[2]

                    if deleted_flag == 0:
                        if self.key_type.startswith("varchar"):
                            key_value = key_value.decode('utf-8').strip()
                        all_entries.append((key_value, record_pos))

        return all_entries

    def rebuild(self):
        all_entries = self._load_all()
        all_entries.sort(key=lambda entry : entry[0])

        with open(self.filename, 'wb') as file:
            file.write(struct.pack(self.HEADER_FORMAT, len(all_entries)))
            
            for key_value, pos in all_entries:
                if self.key_type.startswith("varchar"):
                    size = int(self.key_type[self.key_type.find("(")+1:self.key_type.find(")")])
                    key_value = str(key_value).encode('utf-8')
                    key_value = key_value[:size].ljust(size, b' ')
                
                file.write(struct.pack(self.ENTRY_FORMAT, key_value, pos, 0))

        open(self.aux_filename, 'wb').close()

    def add(self, key, pos):
        if self.key_type.startswith("varchar"):
            size = int(self.key_type[self.key_type.find("(")+1:self.key_type.find(")")])
            key = str(key).encode('utf-8')
            key = key[:size].ljust(size, b' ')
        
        with open(self.aux_filename, 'ab') as aux_file:
            aux_file.write(struct.pack(self.ENTRY_FORMAT, key, pos, 0))
        
        count_main = self._read_header()
        count_aux = self._count_aux_entries()

        if count_aux >= (math.log2(count_main + 1) if count_main > 0 else 1):
            self.rebuild()
    
    def _read_entry_from_main(self, pos):
        if self.ENTRY_SIZE is None:
            raise RuntimeError("Formato de Sequential File no inicializado.")

        with open(self.filename, 'rb') as file:
            offset = self.HEADER_SIZE + pos * self.ENTRY_SIZE
            file.seek(offset)
            data = file.read(self.ENTRY_SIZE)
            if not data or len(data) < self.ENTRY_SIZE:
                return None
            
            unpacked = struct.unpack(self.ENTRY_FORMAT, data)
            key_value = unpacked[0]
            record_pos = unpacked[1]
            deleted_flag = unpacked[2]

            if self.key_type.startswith("varchar"):
                key_value = key_value.decode('utf-8').strip()

            return (key_value, record_pos, deleted_flag)

    def _lower_bound(self, key):
        left = 0
        right = self._read_header() - 1
        result_pos = None

        with open(self.filename, 'r+b') as file:
            while left <= right:
                mid = (left + right) // 2
                entry = self._read_entry_from_main(mid)

                if entry is None:
                    break

                reg_key, _, deleted = entry

                if deleted == 1:
                    left = mid + 1
                    continue

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
                    entry = self._read_entry_from_main(i)
                    if entry is None:
                        break

                    reg_key, pos, deleted = entry
                    if reg_key > key:
                        break

                    # Matcheando
                    if reg_key == key and deleted == 0:
                        matches.append(pos)
                    
                    i += 1

        # Fallback: scanear el auxiliar
        if os.path.exists(self.aux_filename):
            with open(self.aux_filename, 'rb') as aux_file:
                while True:
                    data = aux_file.read(self.ENTRY_SIZE)
                    if not data or len(data) < self.ENTRY_SIZE:
                        break
                    
                    unpacked = struct.unpack(self.ENTRY_FORMAT, data)
                    key_value = unpacked[0]
                    record_pos = unpacked[1]
                    deleted_flag = unpacked[2]

                    if self.key_type.startswith("varchar"):
                        key_value = key_value.decode('utf-8').strip()

                    if key_value == key and deleted_flag == 0:
                        matches.append(record_pos)

        return matches if matches else None

    def rangeSearch(self, begin_key, end_key):
        matches = []
        count = self._read_header()
        pos = self._lower_bound(begin_key)

        if pos is None:
            pos = count

        with open(self.filename, 'rb') as file:
            i = pos
            while i < count:
                entry_data = self._read_entry_from_main(i)
                if entry_data is None:
                    break

                reg_key, pos, deleted = entry_data

                if reg_key > end_key:
                    break

                if deleted == 0 and begin_key <= reg_key <= end_key:
                    matches.append(pos)
                
                i += 1

        # Fallback: scanear el auxiliar
        if os.path.exists(self.aux_filename):
            with open(self.aux_filename, 'rb') as aux_file:
                while True:
                    data = aux_file.read(self.ENTRY_SIZE)
                    if not data or len(data) < self.ENTRY_SIZE:
                        break
                    
                    unpacked = struct.unpack(self.ENTRY_FORMAT, data)
                    key_value = unpacked[0]
                    record_pos = unpacked[1]
                    deleted_flag = unpacked[2]

                    if self.key_type.startswith("varchar"):
                        key_value = key_value.decode('utf-8').strip()

                    if deleted_flag == 0 and begin_key <= key_value <= end_key:
                        matches.append(record_pos)

        return matches if matches else None

    def erase(self, key):
        count = self._read_header()
        pos = self._lower_bound(key)
        deleted_any = False

        if pos is None:
            return False
    
        with open(self.filename, 'r+b') as file:
            i = pos
            while i < count: # Buscamos mas de uno
                offset = self.HEADER_SIZE + i * self.ENTRY_SIZE
                file.seek(offset)
                data = file.read(self.ENTRY_SIZE + 1)
                if len(data) < self.ENTRY_SIZE + 1:
                    break

                unpacked = struct.unpack(self.INDEX_ENTRY_FORMAT, data)
                reg_key = unpacked[0]
                record_pos = unpacked[1]
                deleted = unpacked[2]

                if self.key_type.startswith("varchar"):
                    reg_key = reg_key.decode('utf-8').strip()

                if reg_key == key: # Borramos
                    if deleted == 0:
                        file.seek(offset + self.REG_SIZE - 1)
                        file.write(b'\x01')
                        count -= 1
                        deleted_any = True
                    i += 1
                elif reg_key > key:
                    break
                else:
                    i += 1

        if deleted_any:
            self._write_header(count)

        return deleted_any