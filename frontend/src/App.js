import React, { useState } from "react";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [jsonData, setJsonData] = useState(null); // para la tabla

  const enviarSQL = async () => {
    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      setResponse(JSON.stringify(data, null, 2));
      setJsonData(data);
    } catch (error) {
      setResponse("Error al enviar la consulta.");
      setJsonData(null);
    }
  };

  const verRegistros = async () => {
    try {
      const res = await fetch("http://localhost:8000/select/alumnos");
      const data = await res.json();
      setResponse(JSON.stringify(data, null, 2));
      setJsonData(data);
    } catch (error) {
      console.error("ERROR", error);
      setResponse("ERROR\n" + error.toString());
      setJsonData(null);
    }
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
    <div style={{ padding: "2rem" }}>
      <h2>Mini DB SQL Interface</h2>
      <textarea
        rows="6"
        cols="60"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Escribe una consulta SQL, ej: SELECT * FROM alumnos"
      />
      <br />
      <button onClick={enviarSQL}>Ejecutar</button>
      <button onClick={verRegistros} style={{ marginLeft: "1rem" }}>
        Ver registros
      </button>

      <pre style={{ marginTop: "1rem", background: "#f9f9f9", padding: "1rem" }}>{response}</pre>
      {renderTabla(jsonData)}
    </div>
  );
}

export default App;
