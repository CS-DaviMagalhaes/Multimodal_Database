import struct

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