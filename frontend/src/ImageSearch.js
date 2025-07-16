import React, { useState } from "react";

const IMAGE_BASE_URL = "http://localhost:8000/images/";

function ImageSearch() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [k, setK] = useState(5);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleKChange = (e) => {
    setK(Number(e.target.value));
  };

  const handleSearch = async () => {
    if (!selectedFile) {
      setError("Please upload an image.");
      return;
    }
    setError("");
    setLoading(true);
    setResults([]);

    try {
      const formData = new FormData();
      formData.append('image', selectedFile);
      formData.append('k', k);
      const response = await fetch('http://localhost:8000/image-search', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        setResults(data.results || data.images || []);
      }
    } catch (error) {
      setError(`Search failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-8">
      <h2 className="text-xl font-bold mb-4 text-blue-700">Image Search</h2>
      <div className="flex flex-col md:flex-row gap-4 items-center mb-6">
        <input type="file" accept="image/*" onChange={handleFileChange} className="block w-full md:w-auto text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
        <label className="flex items-center gap-2">
          <span className="text-gray-700 font-medium">Top-k:</span>
          <input
            type="number"
            min={1}
            max={100}
            value={k}
            onChange={handleKChange}
            className="w-20 border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </label>
        <button
          onClick={handleSearch}
        >
          <span>Search</span>
        </button>
      </div>
      {error && <div className="text-red-600 mb-4">{error}</div>}
      {loading && <div className="text-blue-600 mb-4">Searching...</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 mt-6">
        {results.map((result, idx) => {
          const filename = typeof result === 'string' ? result : result.filename || result.image || result;
          const similarity = result.similarity || result.score || '';
          return (
            <div key={idx} className="bg-gray-50 rounded-lg shadow p-4 flex flex-col items-center">
              <img
                src={`${IMAGE_BASE_URL}${filename}`}
                alt={filename}
                className="w-32 h-32 object-cover border border-gray-200 rounded mb-2"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.textContent = `Error loading ${filename}`;
                }}
              />
              <div className="font-semibold text-gray-700 mb-1">{filename}</div>
              {similarity && <div className="text-xs text-gray-500">Similarity: {similarity.toFixed(4)}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ImageSearch; 