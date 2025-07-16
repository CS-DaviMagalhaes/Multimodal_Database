import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

function Home() {
  const navigate = useNavigate();
  const [selectedSearch, setSelectedSearch] = useState("");
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
  const knownTables = ["alumnos"];
  const knownColumns = ["id", "nombre", "edad"];
  const allWords = [...keywords, ...knownTables, ...knownColumns];

  const handleRadioChange = (e) => {
    setSelectedSearch(e.target.value);
    if (e.target.value === "image") navigate("/image-search");
    else if (e.target.value === "audio") navigate("/audio-search");
    else if (e.target.value === "text") navigate("/text-search");
  };

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
      <div className="overflow-x-auto mt-4">
        <table className="min-w-full border border-gray-300 rounded-lg">
          <thead className="bg-gray-100">
            <tr>
              {data.columnas.map((col, i) => (
                <th key={i} className="px-4 py-2 text-left font-semibold text-gray-700">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.registros.map((fila, i) => (
              <tr key={i} className="even:bg-gray-50">
                {data.columnas.map((col, j) => (
                  <td key={j} className="px-4 py-2 text-sm">{fila[col]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <h2 className="text-xl font-bold mb-4 text-blue-700">Mini DB SQL Interface</h2>
      <textarea
        rows="6"
        className="w-full border border-gray-300 rounded p-2 font-mono text-base focus:outline-none focus:ring-2 focus:ring-blue-400"
        value={query}
        onChange={handleInput}
        placeholder="Escribe una consulta SQL, ej: SELECT * FROM alumnos"
      />
      <div className="relative">
        {suggestions.length > 0 && (
          <ul className="absolute bg-white border border-gray-300 rounded w-full mt-1 z-10 max-h-32 overflow-y-auto shadow">
            {suggestions.map((s, i) => (
              <li key={i}
                onClick={() => aplicarSugerencia(s)}
                className={`px-3 py-2 cursor-pointer hover:bg-blue-100 ${i === cursor ? "bg-blue-50" : ""}`}
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex gap-4 mt-4">
        <button
          onClick={enviarSQL}
        >
          <span>Ejecutar</span>
        </button>
        <button
          onClick={verRegistros}
        >
          <span>Ver registros</span>
        </button>
      </div>
      <pre
        className={`mt-4 rounded p-4 text-sm ${status === "error" ? "bg-red-100 border border-red-400 text-red-700" : "bg-gray-100 border border-gray-300 text-gray-800"}`}
      >
        {response}
      </pre>
      {renderTabla(jsonData)}
      <div className="mt-8 pt-6 border-t border-gray-200">
        <h3 className="text-lg font-semibold mb-2 text-blue-700">Buscar por tipo</h3>
        <div className="flex gap-8">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="image"
              checked={selectedSearch === "image"}
              onChange={handleRadioChange}
              className="accent-blue-600"
            />
            <span className="text-gray-700">Image Search</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="audio"
              checked={selectedSearch === "audio"}
              onChange={handleRadioChange}
              className="accent-blue-600"
            />
            <span className="text-gray-700">Audio Search</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              value="text"
              checked={selectedSearch === "text"}
              onChange={handleRadioChange}
              className="accent-blue-600"
            />
            <span className="text-gray-700">Text Search</span>
          </label>
        </div>
      </div>
    </div>
  );
}

export default Home; 