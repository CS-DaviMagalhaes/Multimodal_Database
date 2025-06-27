import csv
from Registro import Registro as Record, IndexEntry, RECORD_SIZE, INDEX_ENTRY_SIZE, BLOCK_FACTOR_DATA, BLOCK_FACTOR_INDEX

class ISAM:
    def __init__(self, data_file, index_file, root_file, overflow_file):
        self.data_file = data_file
        self.index_file = index_file
        self.root_file = root_file
        self.overflow_file = overflow_file

    def build(self, csv_file):
        records = []
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                try:
                    record = Record(
                        int(row[0]),        # id
                        row[1],             # name
                        int(row[2]),        # state_id
                        row[3],             # state_code
                        row[4],             # state_name
                        int(row[5]),        # country_id
                        row[6],             # country_code
                        row[7],             # country_name
                        float(row[8]),      # latitude
                        float(row[9]),      # longitude
                        row[10]             # wikiDataId
                    )
                    records.append(record)
                except Exception as e:
                    print(f"Error al procesar fila: {row} -> {e}")

        records.sort(key=lambda x: x.id)
        index_entries_level1 = []
        root_index_entries = []

        data_offset = 0
        with open(self.data_file, 'wb') as data_f:
            for i in range(0, len(records), BLOCK_FACTOR_DATA):
                page = records[i:i + BLOCK_FACTOR_DATA]
                for rec in page:
                    data_f.write(rec.pack())
                if page:
                    index_entries_level1.append(IndexEntry(page[0].id, data_offset))
                data_offset += BLOCK_FACTOR_DATA * RECORD_SIZE

        index_offset = 0
        with open(self.index_file, 'wb') as index_f:
            for i in range(0, len(index_entries_level1), BLOCK_FACTOR_INDEX):
                page = index_entries_level1[i:i + BLOCK_FACTOR_INDEX]
                for entry in page:
                    index_f.write(entry.pack())
                if page:
                    root_index_entries.append(IndexEntry(page[0].key, index_offset))
                index_offset += BLOCK_FACTOR_INDEX * INDEX_ENTRY_SIZE

        with open(self.root_file, 'wb') as root_f:
            for entry in root_index_entries:
                root_f.write(entry.pack())

        open(self.overflow_file, 'wb').close()

    def search(self, id):
        id = int(id)
        with open(self.root_file, 'rb') as root_f, open(self.index_file, 'rb') as idx_f, open(self.data_file, 'rb') as data_f:
            root_entries = []
            while True:
                data = root_f.read(INDEX_ENTRY_SIZE)
                if not data:
                    break
                entry = IndexEntry.unpack(data)
                if entry:
                    root_entries.append(entry)

            root_entry = None
            for i in range(len(root_entries)):
                if i == len(root_entries)-1 or id < root_entries[i+1].key:
                    root_entry = root_entries[i]
                    break

            if not root_entry:
                return None

            idx_f.seek(root_entry.page_pos)
            index_entries = []
            for _ in range(BLOCK_FACTOR_INDEX):
                data = idx_f.read(INDEX_ENTRY_SIZE)
                if not data:
                    break
                entry = IndexEntry.unpack(data)
                if entry:
                    index_entries.append(entry)

            data_page_offset = None
            for i in range(len(index_entries)):
                if i == len(index_entries)-1 or id < index_entries[i+1].key:
                    data_page_offset = index_entries[i].page_pos
                    break

            if data_page_offset is None:
                return None

            data_f.seek(data_page_offset)
            for _ in range(BLOCK_FACTOR_DATA):
                rec_data = data_f.read(RECORD_SIZE)
                if not rec_data:
                    break
                record = Record.from_bytes(rec_data)
                if record and record.id == id:
                    return record

        with open(self.overflow_file, 'rb') as overflow_f:
            while True:
                rec_data = overflow_f.read(RECORD_SIZE)
                if not rec_data:
                    break
                record = Record.unpack(rec_data)
                if record and record.id == id:
                    return record

        return None

    def range_search(self, begin_id, end_id):
        results = []
        begin_id, end_id = int(begin_id), int(end_id)
        try:
            with open(self.data_file, 'rb') as data_f:
                data_f.seek(0, 2)
                file_size = data_f.tell()
                data_f.seek(0)
                while data_f.tell() < file_size:
                    page_data = data_f.read(BLOCK_FACTOR_DATA * RECORD_SIZE)
                    for i in range(BLOCK_FACTOR_DATA):
                        start = i * RECORD_SIZE
                        end = start + RECORD_SIZE
                        if end > len(page_data):
                            break
                        record_data = page_data[start:end]
                        rec = Record.unpack(record_data)
                        if rec and begin_id <= rec.id <= end_id:
                            results.append(rec)
        except Exception as e:
            print(f"Error en data_pages: {e}")

        try:
            with open(self.overflow_file, 'rb') as overflow_f:
                while True:
                    record_data = overflow_f.read(RECORD_SIZE)
                    if not record_data:
                        break
                    rec = Record.unpack(record_data)
                    if rec and begin_id <= rec.id <= end_id:
                        results.append(rec)
        except Exception as e:
            print(f"Error en overflow: {e}")

        return sorted(results, key=lambda r: r.id)

    def add(self, record):
        if not isinstance(record, Record):
            raise ValueError("Solo se pueden agregar objetos Record")
        with open(self.overflow_file, 'ab') as overflow_f:
            print(type(record.id))
            print(type(record.state_id))
            print(type(record.country_id))
            print(type(record.latitude))
            print(type(record.longitude))

            overflow_f.write(record.pack())

    def remove(self, id):
        id = int(id)
        removed = False
        temp_records = []
        with open(self.overflow_file, 'rb') as overflow_f:
            while True:
                data = overflow_f.read(RECORD_SIZE)
                if not data:
                    break
                record = Record.from_bytes(data)
                if record.id != id:
                    temp_records.append(record)
                else:
                    removed = True
        with open(self.overflow_file, 'wb') as overflow_f:
            for record in temp_records:
                overflow_f.write(record.pack())
        return removed