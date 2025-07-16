import React, { useState } from "react";

function TextSearch() {
  const [query, setQuery] = useState("");
  const [k, setK] = useState(5);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState({}); // Track expanded state by index

  const handleSearch = async () => {
    setLoading(true);
    setError("");
    setResults([]);
    try {
      const response = await fetch("http://localhost:8000/text-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, k }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setResults(data.results || []);
      setExpanded({}); // Reset expanded state on new search
    } catch (err) {
      setError("Search failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = idx => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <h2 className="text-xl font-bold mb-4 text-blue-700">Text Search</h2>
      <div className="flex flex-col md:flex-row gap-4 items-center mb-6">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Enter your text query..."
          className="w-full md:w-2/3 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <label className="flex items-center gap-2">
          <span className="text-gray-700 font-medium">Top-k:</span>
          <input
            type="number"
            min={1}
            max={20}
            value={k}
            onChange={e => setK(Number(e.target.value))}
            className="w-20 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </label>
        <button onClick={handleSearch}>
          <span>Search</span>
        </button>
      </div>
      {error && <div className="text-red-600 mb-4">{error}</div>}
      {loading && <div className="text-blue-600 mb-4">Searching...</div>}
      <div>
        {results.map((result, idx) => {
          const isExpanded = !!expanded[idx];
          return (
            <div
              key={idx}
              className={`bg-gray-50 rounded-lg shadow p-4 mb-4 cursor-pointer transition-all duration-200 ${isExpanded ? 'ring-2 ring-blue-400' : ''}`}
              onClick={() => toggleExpand(idx)}
              title={isExpanded ? 'Click to collapse' : 'Click to expand'}
            >
              <div className="font-semibold text-blue-700 text-lg mb-1">{result.case_title}</div>
              <div className="text-gray-600 mb-1">Outcome: <span className="font-medium">{result.case_outcome}</span></div>
              <div className="text-xs text-gray-500 mb-2">Score: {result.score && result.score.toFixed ? result.score.toFixed(4) : result.score}</div>
              <div className="text-gray-700 text-sm whitespace-pre-line">
                {isExpanded
                  ? (result.case_text || "")
                  : (result.case_text ? result.case_text.slice(0, 300) + (result.case_text.length > 300 ? "..." : "") : "")}
              </div>
              <div className="text-xs text-blue-500 mt-2">{isExpanded ? "Click to collapse" : "Click to expand"}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TextSearch; 