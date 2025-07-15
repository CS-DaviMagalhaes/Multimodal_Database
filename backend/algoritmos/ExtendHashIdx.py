import struct
import os
import json

BUCKET_CAPACITY = 6
GLOBAL_DEPTH_LIMIT = 10 
EMPTY_THRESHOLD = 0.4

class ExtendibleHashIndex:
    def __init__(self, index_name, key_type="int"):
        self.key_type = key_type.lower()
        
        self.meta_file = os.path.join(f"{index_name}.eh.meta")
        self.dir_file = os.path.join(f"{index_name}.eh.dir")
        self.bucket_file = os.path.join(f"{index_name}.eh.buckets")
        
        self.ENTRY_FORMAT = 'ii'  # key, position
        self.ENTRY_SIZE = struct.calcsize(self.ENTRY_FORMAT)
        self.BUCKET_HEADER_FORMAT = 'iii'  # local_depth, next_bucket, size
        self.BUCKET_HEADER_SIZE = struct.calcsize(self.BUCKET_HEADER_FORMAT)
        self.BUCKET_FORMAT = f'iii{BUCKET_CAPACITY*self.ENTRY_FORMAT}'
        self.BUCKET_SIZE = struct.calcsize(self.BUCKET_FORMAT)
        
        self.meta = {}

        if not os.path.exists(self.dir_file):
            self._initialize_new_index()
        else:
            self._load_existing_index()
    
    def _initialize_new_index(self):
        self.meta = {
            'algorithm': 'EH',
            'key_type': self.key_type,
            'global_depth': 1,
            'bucket_count': 2
        }
        self._save_metadata()

        with open(self.dir_file, 'wb') as f:
            f.write(struct.pack('ii', 0, 0))
            f.write(struct.pack('ii', 1, 1))
        
        with open(self.bucket_file, 'wb') as f:
            f.write(struct.pack(self.BUCKET_FORMAT, 1, -1, 0, *[0]*BUCKET_CAPACITY*2))
            f.write(struct.pack(self.BUCKET_FORMAT, 1, -1, 0, *[0]*BUCKET_CAPACITY*2))
    
    def _load_existing_index(self):
        with open(self.meta_file, 'r') as f:
            self.meta = json.load(f)
    
    def _hash_key(self, key):
        if self.key_type == "int":
            key = int(key)
            return bin(key % (2**GLOBAL_DEPTH_LIMIT))[2:].zfill(GLOBAL_DEPTH_LIMIT)
        else:
            return bin(hash(key) % (2**GLOBAL_DEPTH_LIMIT))[2:].zfill(GLOBAL_DEPTH_LIMIT)
    
    def _get_bucket(self, bucket_num):
        with open(self.bucket_file, 'rb') as f:
            f.seek(bucket_num * self.BUCKET_SIZE)
            data = f.read(self.BUCKET_SIZE)
            if not data:
                raise ValueError(f"Bucket {bucket_num} no encontrado")
            
            header = struct.unpack(self.BUCKET_HEADER_FORMAT, data[:self.BUCKET_HEADER_SIZE])
            entries = []
            offset = self.BUCKET_HEADER_SIZE
            for _ in range(BUCKET_CAPACITY):
                entry = struct.unpack(self.ENTRY_FORMAT, data[offset:offset+self.ENTRY_SIZE])
                if entry[0] != 0:
                    entries.append(entry)
                offset += self.ENTRY_SIZE
            
            return {
                'local_depth': header[0],
                'next_bucket': header[1],
                'size': header[2],
                'entries': entries
            }
    
    def _update_bucket(self, bucket_num, bucket_data):
        with open(self.bucket_file, 'r+b') as f:
            f.seek(bucket_num * self.BUCKET_SIZE)
            
            entries = []
            for i in range(BUCKET_CAPACITY):
                if i < len(bucket_data['entries']):
                    entries.extend(bucket_data['entries'][i])
                else:
                    entries.extend([0, 0])
            
            f.write(struct.pack(self.BUCKET_FORMAT,
                bucket_data['local_depth'],
                bucket_data['next_bucket'],
                bucket_data['size'],
                *entries
            ))
    
    def _find_bucket(self, binary_key):
        with open(self.dir_file, 'rb') as f:
            global_depth = self.meta['global_depth']
            suffix = binary_key[-global_depth:] if global_depth > 0 else ''
            
            f.seek(0)
            while True:
                data = f.read(struct.calcsize('ii'))
                if not data:
                    break
                dir_key, bucket_num = struct.unpack('ii', data)
                dir_key = bin(dir_key)[2:].zfill(global_depth)
                if dir_key == suffix:
                    return bucket_num
        return 0
    
    def add(self, key, position):
        binary_key = self._hash_key(key)
        bucket_num = self._find_bucket(binary_key)
        bucket = self._get_bucket(bucket_num)
        current_bucket = bucket_num
        while True:
            bucket = self._get_bucket(current_bucket)
            
            for entry in bucket['entries']:
                if entry[0] == key:
                    return False
            
            if bucket['size'] < BUCKET_CAPACITY:
                bucket['entries'].append((key, position))
                bucket['size'] += 1
                self._update_bucket(current_bucket, bucket)
                return True
            
            if bucket['next_bucket'] == -1:
                break
            current_bucket = bucket['next_bucket']
        
        if bucket['local_depth'] < GLOBAL_DEPTH_LIMIT:
            self._split_bucket(bucket_num, binary_key)
            return self.insert(key, position)
        else:
            self._create_overflow(bucket_num, key, position)
            return True
    
    def _split_bucket(self, bucket_num, binary_key):
        bucket = self._get_bucket(bucket_num)
        new_local_depth = bucket['local_depth'] + 1
        
        with open(self.bucket_file, 'ab') as f:
            new_bucket_num = self.meta['bucket_count']
            f.write(struct.pack(self.BUCKET_FORMAT, new_local_depth, -1, 0, *[0]*BUCKET_CAPACITY*2))
            self.meta['bucket_count'] += 1
        
        prefix_mask = 1 << (GLOBAL_DEPTH_LIMIT - new_local_depth)
        with open(self.dir_file, 'r+b') as f:
            f.seek(0)
            while True:
                pos = f.tell()
                data = f.read(struct.calcsize('ii'))
                if not data:
                    break
                
                dir_key, old_bucket = struct.unpack('ii', data)
                if old_bucket == bucket_num:
                    new_bucket = new_bucket_num if (dir_key & prefix_mask) else bucket_num
                    f.seek(pos)
                    f.write(struct.pack('ii', dir_key, new_bucket))
        
        self._save_metadata()
    
    def _create_overflow(self, bucket_num, key, position):
        with open(self.bucket_file, 'ab') as f:
            last_bucket = bucket_num
            bucket = self._get_bucket(last_bucket)
            while bucket['next_bucket'] != -1:
                last_bucket = bucket['next_bucket']
                bucket = self._get_bucket(last_bucket)
            
            new_bucket_num = self.meta['bucket_count']
            f.write(struct.pack(self.BUCKET_FORMAT,
                bucket['local_depth'],
                -1, 1, key, position, 
                *[0]*(BUCKET_CAPACITY*2 - 2)
            ))
            self.meta['bucket_count'] += 1
            
            bucket['next_bucket'] = new_bucket_num
            self._update_bucket(last_bucket, bucket)
        
        self._save_metadata()
    
    def search(self, key):
        binary_key = self._hash_key(key)
        bucket_num = self._find_bucket(binary_key)
        positions = []
        
        current_bucket = bucket_num
        while current_bucket != -1:
            bucket = self._get_bucket(current_bucket)
            
            for entry in bucket['entries']:
                if entry[0] == key:
                    positions.append(entry[1])
            
            current_bucket = bucket['next_bucket']
        
        return positions if positions else None
    
    def delete(self, key):
        binary_key = self._hash_key(key)
        bucket_num = self._find_bucket(binary_key)
        deleted = False
        
        current_bucket = bucket_num
        while current_bucket != -1:
            bucket = self._get_bucket(current_bucket)
            
            new_entries = [e for e in bucket['entries'] if e[0] != key]
            if len(new_entries) < len(bucket['entries']):
                deleted = True
                bucket['entries'] = new_entries
                bucket['size'] = len(new_entries)
                self._update_bucket(current_bucket, bucket)
            
            current_bucket = bucket['next_bucket']
        
        if deleted:
            self._check_empty_buckets()
        
        return deleted
    
    def _check_empty_buckets(self):
        pass
    
    def _save_metadata(self):
        with open(self.meta_file, 'w') as f:
            json.dump(self.meta, f)
    
    @classmethod
    def create_index(cls, table_name, column_name, key_type="int"):
        index_name = f"{table_name}_{column_name}"
        return cls(index_name, key_type)
    
    def sync_metadata(self):
        self._save_metadata()