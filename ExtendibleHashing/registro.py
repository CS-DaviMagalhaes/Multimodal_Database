"""
ejemplo de data

ISBN;Book-Title;Book-Author;Year-Of-Publication;Publisher
195153448;Classical Mythology;Mark P. O. Morford;2002;Oxford University Press
2005018;Clara Callan;Richard Bruce Wright;2001;HarperFlamingo Canada

ISBN (international standard book number) es un número identificador internacional
para libros, hasta 2006 tenian hasta 10 digitos, pero hoy tienen 13 digitos. La base de datos
tiene numeros de 10 digitos pero pondremos 13 caso se quiera expandirla futuramente con libros actuales*/

Registro de mayor longitud en la columna 'Book-Title': 256 chars
Registro de mayor longitud en la columna 'Book-Author': 143 chars
Registro de mayor longitud en la columna 'Year-Of-Publication': 4 chars
Registro de mayor longitud en la columna 'Publisher': 134 chars
"""
import struct

REGISTER_FORMAT = '256s256s4s256s256s' 
RECORD_SIZE = struct.calcsize(REGISTER_FORMAT) 

class Registro: # Hacer registro de kaggle y después generico para simplificar la vida (20-80)
    def __init__(self, isbn, title, year, author, publisher):
        self.isbn = isbn
        self.title = title
        self.year = year
        self.author = author
        self.publisher = publisher

    # Helper functions

    def get_reg_string(self): # vars(self).values() retorna el valor de todas las variables de la clase
        return " | ".join(str(v) for v in vars(self).values()) # isbn | title | year | ...
        

    def to_fields(self):
        return (
            self.isbn.encode(),
            self.title.encode(),
            self.year.encode(),
            self.author.encode(),
            self.publisher.encode(),
    )

    def print_reg(self):
        print(self.get_reg_string())