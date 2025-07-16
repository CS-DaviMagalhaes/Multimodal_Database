import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import ImageSearch from "./ImageSearch";
import AudioSearch from "./AudioSearch";
import TextSearch from "./TextSearch";
import Home from "./Home";

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-blue-700 text-white shadow p-4 mb-8">
          <h1 className="text-2xl font-bold text-center tracking-wide">Multimodal Database Search</h1>
        </header>
        <main className="max-w-3xl mx-auto px-4">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/image-search" element={<ImageSearch />} />
            <Route path="/audio-search" element={<AudioSearch />} />
            <Route path="/text-search" element={<TextSearch />} />
          </Routes>
        </main>
        <footer className="text-center text-gray-400 text-xs py-6 mt-12">
          &copy; {new Date().getFullYear()} Multimodal Database
        </footer>
      </div>
    </Router>
  );
}

export default App;
