import struct
import os

INDEX_ENTRY_SIZE = struct.calcsize('ii')  # key (int) + position (int)
BLOCK_FACTOR_INDEX = 4

class ISAMIndex:
    def __init__(self, filename):
        self.main_index_filename = f"{filename}.isam"
        self.overflow_filename = f"{filename}.isam.overflow"
        
        if not os.path.exists(self.main_index_filename):
            with open(self.main_index_filename, 'wb') as mf, \
                 open(self.overflow_filename, 'wb') as of:
                pass

    def _write_index_entry(self, file, key, position):
        file.write(struct.pack('ii', int(key), int(position)))

    def _read_index_entries(self, file, count):
        entries = []
        for _ in range(count):
            data = file.read(INDEX_ENTRY_SIZE)
            if len(data) < INDEX_ENTRY_SIZE:
                break
            key, pos = struct.unpack('ii', data)
            if key != -1:
                entries.append((key, pos))
        return entries

    def build(self, keys_positions):
        if not keys_positions:
            return
            
        keys_positions.sort(key=lambda x: x[0])
        total_entries = len(keys_positions)
        pages_needed = (total_entries + BLOCK_FACTOR_INDEX**2 - 1) // BLOCK_FACTOR_INDEX**2
        
        with open(self.main_index_filename, 'wb') as index_f:
            root_entries_pos = index_f.tell()
            index_f.write(b'\x00' * BLOCK_FACTOR_INDEX * INDEX_ENTRY_SIZE)
            root_entries = []
            for i in range(0, total_entries, BLOCK_FACTOR_INDEX**2):
                page_end = min(i + BLOCK_FACTOR_INDEX**2, total_entries)
                first_key = keys_positions[i][0]
                page_pos = index_f.tell()
                root_entries.append((first_key, page_pos))
                
                for key, pos in keys_positions[i:page_end]:
                    self._write_index_entry(index_f, key, pos)
                
                entries_written = page_end - i
                if entries_written < BLOCK_FACTOR_INDEX**2:
                    padding = BLOCK_FACTOR_INDEX**2 - entries_written
                    index_f.write(b'\xFF' * padding * INDEX_ENTRY_SIZE)
            
            index_f.seek(root_entries_pos)
            for key, pos in root_entries:
                self._write_index_entry(index_f, key, pos)
            
            if len(root_entries) < BLOCK_FACTOR_INDEX:
                padding = BLOCK_FACTOR_INDEX - len(root_entries)
                index_f.write(b'\xFF' * padding * INDEX_ENTRY_SIZE)

    def add(self, key, position):
        with open(self.overflow_filename, 'ab') as f:
            self._write_index_entry(f, key, position)

    def search(self, key):
        key = int(key)
        positions = []
        
        try:
            with open(self.main_index_filename, 'rb') as index_f:
                root_entries = self._read_index_entries(index_f, BLOCK_FACTOR_INDEX)
                
                page_pos = None
                for i in range(len(root_entries)):
                    if i == len(root_entries)-1 or key < root_entries[i+1][0]:
                        page_pos = root_entries[i][1]
                        break
                
                if page_pos is not None:
                    index_f.seek(page_pos)
                    page_entries = self._read_index_entries(index_f, BLOCK_FACTOR_INDEX**2)
                    
                    for k, pos in page_entries:
                        if k == key:
                            positions.append(pos)
        except Exception as e:
            print(f"Error en main en search(): {e}")
        
        try:
            if os.path.exists(self.overflow_filename):
                with open(self.overflow_filename, 'rb') as f:
                    while True:
                        data = f.read(INDEX_ENTRY_SIZE)
                        if not data:
                            break
                        if len(data) != INDEX_ENTRY_SIZE:
                            break
                        k, pos = struct.unpack('ii', data)
                        if k == key:
                            positions.append(pos)
        except Exception as e:
            print(f"Error en overflow en search(): {e}")
        
        return positions if positions else None

    def rangeSearch(self, min_key, max_key):
        min_key, max_key = int(min_key), int(max_key)
        positions = []
        
        try:
            with open(self.main_index_filename, 'rb') as index_f:
                root_entries = self._read_index_entries(index_f, BLOCK_FACTOR_INDEX)
                
                start_page = 0
                while start_page < len(root_entries) - 1 and root_entries[start_page + 1][0] <= min_key:
                    start_page += 1
                
                for i in range(start_page, len(root_entries)):
                    root_key, root_pos = root_entries[i]
                    
                    if root_key > max_key and i > 0:
                        break
                    
                    index_f.seek(root_pos)
                    page_entries = self._read_index_entries(index_f, BLOCK_FACTOR_INDEX**2)
                    
                    for key, pos in page_entries:
                        if key > max_key:
                            break
                        if min_key <= key <= max_key:
                            positions.append(pos)
        
        except Exception as e:
            print(f"Error en main en rangeSearch(): {e}")
        
        try:
            if os.path.exists(self.overflow_filename):
                with open(self.overflow_filename, 'rb') as f:
                    while True:
                        data = f.read(INDEX_ENTRY_SIZE)
                        if not data:
                            break
                        
                        key, pos = struct.unpack('ii', data)
                        if key > max_key:
                            break
                        if min_key <= key <= max_key:
                            positions.append(pos)
        except Exception as e:
            print(f"Error en overflow en rangeSearch(): {e}")
        
        return positions
