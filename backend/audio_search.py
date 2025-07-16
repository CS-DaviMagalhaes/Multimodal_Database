import numpy as np
import joblib
import librosa
import tempfile
import os

class AudioSearchEngine:
    def __init__(self):
        # Load descriptors and filenames
        data = np.load("audio_descriptors/descriptors.npz", allow_pickle=True)
        self.filenames = data["filenames"]
        # Load kmeans model
        self.kmeans = joblib.load("audio_descriptors/kmeans_model.pkl")
        # Load tf-idf and idf
        tfidf_data = np.load("audio_descriptors/tfidf_data.npz", allow_pickle=True)
        self.tf_idf = tfidf_data["tf_idf"]
        self.idf = tfidf_data["idf"]

    def create_query_histogram(self, audio_data):
        # Save to temp file and load with librosa
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name
        y, sr = librosa.load(temp_path, sr=None)
        os.unlink(temp_path)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).T
        histogram = np.zeros(self.kmeans.n_clusters, dtype=int)
        if mfcc is not None and len(mfcc) > 0:
            cluster_assignments = self.kmeans.predict(mfcc)
            for idx in cluster_assignments:
                histogram[idx] += 1
        histogram = histogram.astype(float)
        histogram /= np.sum(histogram) if np.sum(histogram) > 0 else 1
        return histogram

    def search(self, audio_data, k=5):
        query_hist = self.create_query_histogram(audio_data)
        query_tfidf = query_hist * self.idf
        heap = []
        for i, hist in enumerate(self.tf_idf):
            dot = np.dot(query_tfidf, hist)
            norm_query = np.linalg.norm(query_tfidf)
            norm_hist = np.linalg.norm(hist)
            cosine_sim = 0
            if norm_query != 0 and norm_hist != 0:
                cosine_sim = dot / (norm_query * norm_hist)
            heap.append((cosine_sim, self.filenames[i]))
        # Get top-k
        top_k = sorted(heap, reverse=True)[:k]
        return [{"filename": fname + ".wav", "similarity": float(sim)} for sim, fname in top_k] 