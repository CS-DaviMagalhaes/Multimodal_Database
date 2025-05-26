import sqlparse

def parse_create_table(query):
    parsed = sqlparse.parse(query)[0]
    tokens = [t for t in parsed.tokens if not t.is_whitespace]

    table_name = None
    columns_raw = None

    for token in tokens:
        if token.ttype is None and "table" in token.value.lower():
            continue  # saltar la palabra TABLE
        if token.ttype is None and table_name is None and "(" not in token.value:
            table_name = token.value.strip()
        if token.ttype is None and "(" in token.value:
            columns_raw = token.value.strip()[1:-1]  # quitar paréntesis

    if not table_name or not columns_raw:
        return None

    columnas = []
    campos = columns_raw.split(",")
    for campo in campos:
        partes = campo.strip().split()
        if len(partes) < 2:
            continue  # evitar columnas mal definidas
        nombre = partes[0]
        tipo = partes[1]
        pk = any(p.lower() == "pk" or p.lower() == "primary" for p in partes)
        columnas.append({"nombre": nombre, "tipo": tipo, "pk": pk})

    return {"tabla": table_name, "columnas": columnas}

def parse_insert(query):
    try:
        query = query.strip().lower()
        tokens = query.replace("(", " ").replace(")", " ").replace(",", " ").split()
        tabla = tokens[2]
        valores = query[query.find("values")+6:].strip()
        valores = valores.strip("(); \n").split(",")
        valores = [v.strip().strip("'").strip('"') for v in valores]
        return {"tabla": tabla, "valores": valores}
    except Exception:
        return None

def extraer_tabla_from_select(query):
    query = query.lower().strip()
    if "from" in query:
        return query.split("from")[1].strip().split()[0]
    return None
