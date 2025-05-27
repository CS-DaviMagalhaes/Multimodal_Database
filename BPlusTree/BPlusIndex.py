import os,struct,csv


class Register:
    FORMAT = "i"
    def __init__(self,id = -1):
        self.id = id
    def empaquetar(self):
        return struct.pack(self.FORMAT,self.id)
    def desempaquetar(self,datos):
        id = struct.unpack(self.FORMAT,datos)
        return Register(id[0])
class Node:
    def __init__(self,m=3,tipo='int'):
        self.tipo = tipo
        if(tipo=="str"):
            self.FORMAT = f'{30}s' * m
            self._keys = [] ### strings de tamaño 30 o ints depende del setter
        else:
            self.FORMAT = 'i' * m
            self._keys = []
        self.hijos = []
        self.pos_registers = []
        self.leaf = True
        self.size = 0
        self.next = -1

        self.FORMAT = self.FORMAT + ('i' * (m + 1)) + ('i' * m) + '?ii'
        self.RECORD_SIZE = struct.calcsize(self.FORMAT)

        self.m = m
    def empaquetar(self):
        if isinstance(self._keys[0], str):
            keys = [k.encode('utf-8') for k in self._keys]
            keys += [b''.ljust(30, b'\x00')] * (self.m - len(keys))
        else:
            keys = self._keys + [-1] * (self.m - len(self._keys))

        # Rellenar hijos
        hijos = self.hijos + [-1] * ((self.m + 1) - len(self.hijos))

        # Rellenar registros
        pos_regs = self.pos_registers + [-1] * (self.m - len(self.pos_registers))

        return struct.pack(
            self.FORMAT,
            *keys,
            *hijos,
            *pos_regs,
            self.leaf,
            self.size,
            self.next
        )
    def desempaquetar(self, data_bytes):
        unpacked = struct.unpack(self.FORMAT, data_bytes)
        idx = 0

        # Leer todas las keys
        if self.tipo == 'str':
            all_keys = [
                unpacked[idx + i].decode('utf-8').strip('\x00')
                for i in range(self.m)
            ]
        else:
            all_keys = list(unpacked[idx:idx + self.m])
        idx += self.m

        # hijos
        all_hijos = list(unpacked[idx:idx + self.m + 1])
        idx += self.m + 1

        # pos_registers
        all_pos = list(unpacked[idx:idx + self.m])
        idx += self.m

        # leaf
        self.leaf = unpacked[idx]
        idx += 1

        # size
        self.size = unpacked[idx]
        idx += 1

        # next
        self.next = unpacked[idx]

        # Guardar solo los valores válidos en memoria
        self._keys = all_keys[:self.size]
        if self.leaf:
            self.pos_registers = all_pos[:self.size]
            self.hijos = []  # hojas no usan hijos
        else:
            self.hijos = all_hijos[:self.size + 1]
            self.pos_registers = []  # internos no usan registros
    ## Si no es nodo hoja el hijo insertado va a la pos donde queda
    # el nodo hoja + 1. Desplaza los demas a la derecha
    def insertar_ordenado(self, nueva_key, nuevo_hijo_o_pos):
        if self.leaf:
            self._keys.append(nueva_key)
            self.pos_registers.append(nuevo_hijo_o_pos)

            # Ordenar por clave manteniendo alineamiento
            combinados = list(zip(self._keys, self.pos_registers))
            combinados.sort(key=lambda x: x[0])
            self._keys, self.pos_registers = zip(*combinados)

            # Convertir de nuevo a lista
            self._keys = list(self._keys)
            self.pos_registers = list(self.pos_registers)

            # Actualizar size
            self.size = len(self._keys)

        else:
            pos = 0
            while pos < self.size and self._keys[pos] < nueva_key:
                pos += 1

            # Insertar la clave en su lugar ordenado
            self._keys.insert(pos, nueva_key)

            # Insertar el hijo a la derecha de la clave insertada
            self.hijos.insert(pos + 1, nuevo_hijo_o_pos)

            # No se recorta self._keys ni self.hijos aquí para permitir desbordamiento
            self.size += 1  # El tamaño real aumenta, ya que aún no se hace split
    def get_hijo_pos(self, clave):
        if self.leaf:
            raise Exception("No se puede buscar hijo en un nodo hoja.")

        for i in range(self.size):
            if clave < self._keys[i]:
                return self.hijos[i]
        return self.hijos[self.size]  # mayor que todas las keys
    def prettyPrint(self):
        if(self.leaf):
            print("Keys: ",self._keys)
            print("Pos Registers:",self.pos_registers)
            print("Size:",self.size)
            print("Next:",self.next)
            #print("M",self.m)
        else:
            print("Keys: ", self._keys)
            print("Pos Hijos:", self.hijos)
            print("Size:", self.size)
            #print("M", self.m)
class BPlusIndex:
        def __init__(self, filename,m=3,tipo="int"):
            self.filename = filename
            self.m = m
            self.tipo = tipo
            if not os.path.exists(self.filename):
                with open(self.filename, "wb") as file:
                    print("Se creo el archivo",self.filename)
                    ### Estructura del header [POSROOT,POSLIBRE,POSELIMINADO]
                    # El eliminado hara una especie de freelist
                    # POSLIBRE dara la pos exacta de un espacio libre para la insercion y tambien la cant de registros

                    file.write(struct.pack('iii',0,0,-1))
                    file.close()
        def getHeader(self,file):
            #with (open(self.filename, "rb") as file):
                file.seek(0)
                header_data = file.read(struct.calcsize('iii'))
                header = struct.unpack('iii', header_data)
                # persona = self.readRecord(pos)
                return header
        def setHeader(self,header_start,file):
            #with (open(self.filename, "r+b") as file):
                file.seek(0)
                file.write(struct.pack('iii',header_start))
        def getRecord(self, pos,file):
            nodo = Node(self.m,self.tipo)
            file.seek(12+pos*nodo.RECORD_SIZE)
            nodoDataPack = file.read(nodo.RECORD_SIZE)
            if not nodoDataPack:
                print("Node not found")
                return
            nodo.desempaquetar(nodoDataPack)
            return nodo
        def noFileGetRecord(self, pos):
            with open(self.filename,"r+b") as file:
                nodo = Node(self.m,self.tipo)
                file.seek(12+pos*nodo.RECORD_SIZE)
                nodoDataPack = file.read(nodo.RECORD_SIZE)
                if not nodoDataPack:
                    print("Node not found")
                    return
                nodo.desempaquetar(nodoDataPack)
                return nodo
        def split_node(self, nodo):
            mid_index = nodo.size // 2

            # Crear nuevo nodo del mismo tipo
            nuevo_nodo = Node(m=nodo.m, tipo=nodo.tipo)
            nuevo_nodo.leaf = nodo.leaf

            if nodo.leaf:
                # --------------------------
                # Caso: Nodo hoja
                # --------------------------
                nuevo_nodo._keys = nodo._keys[mid_index:]
                nuevo_nodo.pos_registers = nodo.pos_registers[mid_index:]

                nodo._keys = nodo._keys[:mid_index]
                nodo.pos_registers = nodo.pos_registers[:mid_index]

                # Actualizar sizes
                nodo.size = len(nodo._keys)
                nuevo_nodo.size = len(nuevo_nodo._keys)

                # La clave que se COPIA al padre (no se elimina del nuevo nodo hoja)
                clave_a_copiar = nuevo_nodo._keys[0]

                return clave_a_copiar, nuevo_nodo

            else:
                # --------------------------
                # Caso: Nodo interno
                # --------------------------
                clave_a_promover = nodo._keys[mid_index]

                # Nodo izquierdo (se queda en `nodo`)
                claves_izq = nodo._keys[:mid_index]
                hijos_izq = nodo.hijos[:mid_index + 1]

                # Nodo derecho (nuevo_nodo)
                claves_der = nodo._keys[mid_index + 1:]
                hijos_der = nodo.hijos[mid_index + 1:]

                nodo._keys = claves_izq
                nodo.hijos = hijos_izq

                nuevo_nodo._keys = claves_der
                nuevo_nodo.hijos = hijos_der

                nodo.size = len(nodo._keys)
                nuevo_nodo.size = len(nuevo_nodo._keys)

                return clave_a_promover, nuevo_nodo
        def add(self,key,key_pos):
            with (open(self.filename, "r+b") as file):
                ###[POSROOT,POSLIBRE,POSELIMINADO]
                headers = self.getHeader(file)
                ###
                if(headers[1]==0): ## Significa que no hay ningun nodo creado en el archivo
                    nodoInsertar = Node(self.m,self.tipo)
                    nodoInsertar.insertar_ordenado(key,key_pos)
                    data = nodoInsertar.empaquetar()
                    file.seek(0, 2)
                    file.write(data)
                    file.seek(4)
                    file.write(struct.pack('i',headers[1]+1))
                else:
                    nodoTemp = self.getRecord(headers[0],file) ### Root para busqueda a hoja
                    nodosPadreListaPos = []
                    nodosPadreListaPos.append(headers[0]) ### Guardo la pos del root para futuros balanceos si es necesario
                    nodoActualFull = False
                    while(True):### Este es el while de busqueda, llegara hasta el nodo hoja correcto e insertara el nodo en la pos correcta a menos que este lleno
                        if(nodoTemp.leaf):
                            nodoTemp.insertar_ordenado(key,key_pos)
                            if(nodoTemp.size>nodoTemp.m):
                                nodoActualFull = True
                                break
                            else:
                                file.seek(12+(nodosPadreListaPos[-1]*nodoTemp.RECORD_SIZE))
                                file.write(nodoTemp.empaquetar())
                                break
                        else:
                            nodosPadreListaPos.append(nodoTemp.get_hijo_pos(key))
                            nodoTemp = self.getRecord(nodosPadreListaPos[-1],file)

                    if(nodoActualFull):
                        print("El nodo de la pos: ", nodosPadreListaPos[-1], "se lleno")
                        nodoActualFull=False
                        if (len(nodosPadreListaPos) == 1):  ### Osea solo hubo 1 nodo existente, por ende hay que crear 2 nodos.
                            clavePadre, nodoTempNext = self.split_node(nodoTemp)  ### El parametro insertado es el nodo izq y el retornado el derecho

                            nodoTemp.next = headers[1]  ## El atributo next del nodo hijo izquierdo apunta a la pos del nuevo nodo derecho creado

                            nodoPadre = Node(self.m, self.tipo)  ## Creo el nodo padre
                            nodoPadre.leaf = False
                            nodoPadre._keys = [clavePadre]
                            nodoPadre.hijos = [headers[0], headers[1]]
                            nodoPadre.size = 1

                            file.seek(0)
                            file.write(struct.pack('ii', headers[1] + 1, headers[1] + 2))
                            file.seek(12 + headers[0] * nodoTemp.RECORD_SIZE)
                            file.write(nodoTemp.empaquetar())
                            file.seek(0, 2)
                            file.write(nodoTempNext.empaquetar())
                            file.write(nodoPadre.empaquetar())

                        else:
                            #### NODO HOJA
                            clavePadre, nodoTempNext = self.split_node(
                                nodoTemp)  ### El parametro insertado es el nodo izq y el retornado el derecho
                            nodoPadre = self.getRecord(nodosPadreListaPos[len(nodosPadreListaPos) - 2], file)
                            nodoPadre.insertar_ordenado(clavePadre, headers[1])

                            nodoTempNext.next = nodoTemp.next
                            nodoTemp.next = headers[1]

                            file.seek(4)
                            file.write(struct.pack('i', headers[1] + 1))

                            if(nodoPadre.size>nodoPadre.m):
                                nodoActualFull=True
                            else:
                                file.seek(12 + nodosPadreListaPos[len(nodosPadreListaPos) - 2] * nodoPadre.RECORD_SIZE)
                                file.write(nodoPadre.empaquetar())

                            file.seek(12 + nodosPadreListaPos[len(nodosPadreListaPos) - 1] * nodoTemp.RECORD_SIZE)
                            file.write(nodoTemp.empaquetar())

                            file.seek(0, 2)
                            file.write(nodoTempNext.empaquetar())

                            contador = 2
                            while(nodoActualFull): ### Este es el while donde se hara una busqueda de abajo hacia arriba para insertar los padres si es necesario claro
                                #nodoTemp=self.getRecord(nodosPadreListaPos[len(nodosPadreListaPos)-contador],file)

                                nodoTemp=nodoPadre
                                if(nodoTemp.size<=nodoTemp.m):
                                    break
                                headers=self.getHeader(file)
                                clavePadre, nodoTempNext = self.split_node(nodoTemp)

                                if (headers[0] == nodosPadreListaPos[len(nodosPadreListaPos) - contador]):  ###Estas en el root
                                    nodoPadre = Node(self.m, self.tipo)  ## Creo el nodo padre

                                    nodoPadre.leaf = False
                                    nodoPadre._keys = [clavePadre]
                                    nodoPadre.hijos = [headers[0], headers[1]]
                                    nodoPadre.size = 1

                                    file.seek(0)
                                    file.write(struct.pack('ii', headers[1] + 1, headers[1] + 2))
                                    file.seek(12 + headers[0] * nodoTemp.RECORD_SIZE)
                                    file.write(nodoTemp.empaquetar())
                                    file.seek(0, 2)
                                    file.write(nodoTempNext.empaquetar())
                                    file.write(nodoPadre.empaquetar())
                                else:
                                    nodoPadre = self.getRecord(nodosPadreListaPos[len(nodosPadreListaPos) - (contador + 1)],file)

                                    nodoPadre.insertar_ordenado(clavePadre,headers[1])

                                    file.seek(4)
                                    file.write(struct.pack('i', headers[1] + 1))

                                    if (nodoPadre.size > nodoPadre.m):
                                        nodoActualFull = True
                                    else:
                                        file.seek(12 + nodosPadreListaPos[len(nodosPadreListaPos) - (contador + 1)] * nodoPadre.RECORD_SIZE)
                                        file.write(nodoPadre.empaquetar())

                                    file.seek(
                                        12 + nodosPadreListaPos[len(nodosPadreListaPos) - contador] * nodoTemp.RECORD_SIZE)
                                    file.write(nodoTemp.empaquetar())

                                    file.seek(0, 2)
                                    file.write(nodoTempNext.empaquetar())
                                contador+=1









                file.close()
        def load(self):
            print("CARGANDO TODOS LOS REGISTROS")
            print("Nombre del archivo:",filename,"Cantidad de key por nodo:",self.m)
            print("Tipo de key:",self.tipo)
            with open(self.filename, "rb") as file:
                ###[POSROOT,POSLIBRE,POSELIMINADO]
                headers = self.getHeader(file)
                print("Aca estan los headers: POSROOT:",headers[0],"POSFREEREG",headers[1],"NEXTDELPOS",headers[2])
                print("------------")
                if(headers[1]==0):
                    print("B+ Index Vacio")
                else:
                    for x in range(headers[1]):
                        tempoNode = self.getRecord(x,file)
                        if(tempoNode.leaf):
                            print("Nodo Hoja",x+1,"con posicion",x)
                        else:
                            print("Nodo Interno", x + 1, "con posicion", x)
                        tempoNode.prettyPrint()
                        print("###################")



                file.close()
        def remove(self,pos):
            with open(self.filename, "r+b") as file:
               file.close()
        def rangeSearch(self,k1,k2):
            with (open(self.filename, "r+b") as file):
                headers = self.getHeader(file)
                actualnode = self.getRecord(headers[0],file)
                while(True):
                    #actualnode.prettyPrint()
                    if(actualnode.leaf):
                        break

                    val = actualnode.hijos[actualnode.size]
                    for x in range(actualnode.size):
                        if(actualnode._keys[x]>k1):
                            val = actualnode.hijos[x]
                            break
                    actualnode = self.getRecord(val,file)
                banderita = True
                iter = 0
                while(banderita):
                    #actualnode.prettyPrint()
                    for key in actualnode._keys:
                        if (k1 <= key):
                            print(key, end=', ')
                        if(k2<=key):
                            banderita=False
                            break

                    actualnode = self.getRecord(actualnode.next,file)
                    iter+=1

                print(" ")
                print(iter)

        def search(self,key):
            with (open(self.filename, "r+b") as file):
                headers = self.getHeader(file)
                actualnode = self.getRecord(headers[0], file)
                while (True):
                    if (actualnode.leaf):
                        break
                    val = actualnode.hijos[actualnode.size]
                    for x in range(actualnode.size):

                        if (actualnode._keys[x] > key):
                            val = actualnode.hijos[x]
                            break


                    actualnode = self.getRecord(val, file)
                for _key in actualnode._keys:
                    if(key==_key):
                        print("Key FOUND:",key)
                        return
                print("Key not found")

def addnode(pair,Bplus):
    Bplus.add(pair[0],pair[1])


def insertar_desde_csv(ruta_csv, bplus, columna_clave="id"):
    with open(ruta_csv, newline='', encoding='utf-8') as csvfile:
        lector = csv.DictReader(csvfile)
        for posicion, fila in enumerate(lector, start=1):
            clave = fila[columna_clave]
            try:
                clave_int = int(clave) if bplus.tipo == "int" else clave
                bplus.add(clave_int, posicion)
            except Exception as e:
                print(f"Error insertando clave '{clave}' en la posición {posicion}: {e}")

filename="Bplus_V1.bin"
BPlus = BPlusIndex(filename,3,"int")

#print("Se insertaran los datos")
#insertar_desde_csv("cities.csv", BPlus, columna_clave="id")
print("Se insertaron los datos")
BPlus.rangeSearch(1000,1010)
print("#########")
BPlus.search(1000)
print("#########")

'''

'''
'''
pair1 = (15,1)
pair2 = (6,4)
pair3 = (1,3)
pair4 = (25,100)
pair5 = (8,120)
pair6 = (20,120)
pair7 = (5,120)
pair8 = (18,120)
pair9 = (2,120)
pair10 = (7,120)
pair11 = (19,120)
pair12 = (21,120)
####################
pair13 = (13,120)
pair14 = (10,120)
pair15 = (12,120)
pair16 = (9,120)
#######
pair17 = (11,120)
pair18 = (4,120)
pair19 = (14,120)
#pair20 = (50,120)
############
pair21 = (16,120)
pair22 = (50,120)
pair23 = (55,120)
pair24 = (80,120)
pair25 = (24,120)
pair26 = (30,120)
#### Funca
pair27 = (22,120)
pair28 = (23,120)
pair29 = (23,120)


print("##########################")
#BPlus.add(pair1[0],pair1[1])
addnode(pair1,BPlus)
####
addnode(pair2,BPlus)
addnode(pair3,BPlus)
################################

addnode(pair4,BPlus)
addnode(pair5,BPlus)
addnode(pair6,BPlus)
addnode(pair7,BPlus)
addnode(pair8,BPlus)
addnode(pair9,BPlus)
addnode(pair10,BPlus)
addnode(pair11,BPlus)
addnode(pair12,BPlus)
addnode(pair13,BPlus)
addnode(pair14,BPlus)
addnode(pair15,BPlus)
addnode(pair16,BPlus)
addnode(pair17,BPlus)
addnode(pair18,BPlus)
addnode(pair19,BPlus)

### FUNCA
addnode(pair21,BPlus)
addnode(pair22,BPlus)
addnode(pair23,BPlus)
addnode(pair24,BPlus)
addnode(pair25,BPlus)
addnode(pair26,BPlus)

### Funca
addnode(pair27,BPlus)
addnode(pair28,BPlus)
addnode(pair29,BPlus)



print("##########################")
BPlus.load()
BPlus.rangeSearch(5,15)


os.remove(BPlus.filename)

'''


#testeo = BPlusIndex("BplusTesting")
#Nodo1 = Node()
#os.remove(testeo.filename)
