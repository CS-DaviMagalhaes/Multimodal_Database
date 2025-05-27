import React, { useState, useEffect } from "react";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [jsonData, setJsonData] = useState(null);
  const [status, setStatus] = useState("idle");
  const [suggestions, setSuggestions] = useState([]);
  const [cursor, setCursor] = useState(0);

  const keywords = [
    "SELECT", "FROM", "WHERE", "INSERT INTO", "VALUES", "CREATE TABLE", "CREATE INDEX",
    "ON", "USING", "BETWEEN", "AND", "OR", "PK", "INT", "VARCHAR"
  ];

  const knownTables = ["alumnos"]; // Puedes llenar esto dinámicamente si deseas
  const knownColumns = ["id", "nombre", "edad"]; // igual

  const allWords = [...keywords, ...knownTables, ...knownColumns];

  const enviarSQL = async () => {
    try {
      setStatus("idle");
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      const esError = data.error || (Array.isArray(data) && data.some(d => d.error));
      setResponse(JSON.stringify(data, null, 2));
      setJsonData(data?.columnas && data?.registros ? data : null);
      setStatus(esError ? "error" : "success");
    } catch (error) {
      setResponse("Error al enviar la consulta.");
      setJsonData(null);
      setStatus("error");
    }
  };

  const verRegistros = async () => {
    try {
      setStatus("idle");
      const res = await fetch("http://localhost:8000/select/alumnos");
      const data = await res.json();
      setResponse(JSON.stringify(data, null, 2));
      setJsonData(data);
      setStatus(data.error ? "error" : "success");
    } catch (error) {
      setResponse("ERROR\n" + error.toString());
      setJsonData(null);
      setStatus("error");
    }
  };

  const handleInput = (e) => {
    const texto = e.target.value;
    setQuery(texto);
    const palabras = texto.split(/\s+/);
    const ultima = palabras[palabras.length - 1].toUpperCase();

    if (ultima.length > 0) {
      const match = allWords.filter(w => w.startsWith(ultima));
      setSuggestions(match.slice(0, 5));
    } else {
      setSuggestions([]);
    }
  };

  const aplicarSugerencia = (sugerencia) => {
    const palabras = query.split(/\s+/);
    palabras[palabras.length - 1] = sugerencia;
    setQuery(palabras.join(" ") + " ");
    setSuggestions([]);
  };

  const renderTabla = (data) => {
    if (!data || !data.columnas || !data.registros) return null;

    return (
      <table border="1" style={{ marginTop: "1rem", borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            {data.columnas.map((col, i) => (
              <th key={i} style={{ padding: "8px", background: "#f0f0f0" }}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.registros.map((fila, i) => (
            <tr key={i}>
              {data.columnas.map((col, j) => (
                <td key={j} style={{ padding: "8px" }}>{fila[col]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h2>Mini DB SQL Interface</h2>

      <textarea
        rows="6"
        cols="60"
        value={query}
        onChange={handleInput}
        placeholder="Escribe una consulta SQL, ej: SELECT * FROM alumnos"
        style={{ fontFamily: "monospace", fontSize: "1rem" }}
      />

      <div style={{ position: "relative" }}>
        {suggestions.length > 0 && (
          <ul style={{
            position: "absolute",
            background: "#fff",
            border: "1px solid #ccc",
            marginTop: "0",
            listStyle: "none",
            padding: "0",
            width: "100%",
            maxHeight: "120px",
            overflowY: "auto",
            zIndex: 999
          }}>
            {suggestions.map((s, i) => (
              <li key={i}
                onClick={() => aplicarSugerencia(s)}
                style={{
                  padding: "6px",
                  cursor: "pointer",
                  background: i === cursor ? "#eee" : "#fff"
                }}>
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>

      <br />
      <button onClick={enviarSQL}>Ejecutar</button>
      <button onClick={verRegistros} style={{ marginLeft: "1rem" }}>
        Ver registros
      </button>

      <pre
        style={{
          marginTop: "1rem",
          background: status === "error" ? "#ffe0e0" : "#f9f9f9",
          border: status === "error" ? "1px solid red" : "1px solid #ccc",
          padding: "1rem",
          color: status === "error" ? "red" : "black"
        }}
      >
        {response}
      </pre>

      {renderTabla(jsonData)}
    </div>
  );
}

export default App;
