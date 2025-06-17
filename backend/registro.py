import struct
import os

class Registro:
    def __init__(self, tabla, columnas):
        self.tabla = tabla
        self.columnas = columnas
        self.format_str = self._generar_format()
        self.filename = os.path.join("tablas", f"{tabla}.tbl")

    def _generar_format(self):
        formato = ""
        for col in self.columnas:
            tipo = col["tipo"].lower()
            if tipo == "int":
                formato += "i"
            elif tipo.startswith("varchar"):
                tam = int(tipo[tipo.find("(")+1:tipo.find(")")])
                formato += f"{tam}s"
            else:
                raise ValueError(f"Tipo no soportado: {tipo}")
        return formato

    def serializar(self, valores):
        if len(valores) != len(self.columnas):
            raise ValueError("Cantidad de valores no coincide con columnas")

        formateados = []
        for i, col in enumerate(self.columnas):
            tipo = col["tipo"].lower()
            val = valores[i]
            if tipo == "int":
                formateados.append(int(val))
            elif tipo.startswith("varchar"):
                tam = int(tipo[tipo.find("(")+1:tipo.find(")")])
                val = str(val).encode("utf-8")
                val = val[:tam].ljust(tam, b" ")
                formateados.append(val)
        return struct.pack(self.format_str, *formateados)

    def insertar(self, valores):
        # Validar duplicados en campos PK
        registros_actuales = self.leer_todos()

        for i, col in enumerate(self.columnas):
            if col["pk"]:
                nuevo_valor_pk = valores[i]
                for fila in registros_actuales:
                    if str(fila[i]) == str(nuevo_valor_pk):
                        raise ValueError(f"Valor duplicado en columna PK '{col['nombre']}': {nuevo_valor_pk}")

        # Insertar el nuevo registro en binario
        data = self.serializar(valores)
        with open(self.filename, "ab") as f:
            f.write(data)

    def leer_todos(self):
        registros = []
        size = struct.calcsize(self.format_str)
        with open(self.filename, "rb") as f:
            while chunk := f.read(size):
                unpacked = struct.unpack(self.format_str, chunk)
                fila = []
                for i, col in enumerate(self.columnas):
                    tipo = col["tipo"].lower()
                    if tipo.startswith("varchar"):
                        fila.append(unpacked[i].decode("utf-8").strip())
                    else:
                        fila.append(unpacked[i])
                registros.append(fila)
        return registros

        registros = []
        struct_size = struct.calcsize(self.format_str)

        with open(f"{self.tabla}.tbl", "rb") as f:
            while chunk := f.read(struct_size):
                unpacked = struct.unpack(self.format_str, chunk)
                fila = []
                for i, col in enumerate(self.columnas):
                    if col["tipo"].startswith("varchar"):
                        val = unpacked[i].decode("utf-8").strip()
                    else:
                        val = unpacked[i]
                    fila.append(val)
                registros.append(fila)
        return registros

    def to_fields(self):
        values = [i for i in vars(self).values()]

        for i in values:
            if isinstance(i, str):
                i = i.encode()
        
        return (i for i in values)

    def pack(self):
        return struct.pack(
            self.format_str,
            *self.to_fields()
        )

    @classmethod
    def unpack(cls, byte_data):
        unpacked = struct.unpack(Registro.format_str, byte_data)
        
        for i in unpacked:
            if isinstance(i, str):
                i = i.decode().strip()
        
        return cls(i for i in unpacked)

    def get_format(self):
        return self.format_str