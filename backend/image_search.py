import numpy as np
import cv2
import joblib
import os
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from collections import defaultdict
import heapq
from PIL import Image
import io

class ImageSearchEngine:
    def __init__(self, dataset_path="C:/Users/davie/Downloads/fashion_small/images/"):
        self.dataset_path = dataset_path
        self.n_components = 70
        self.n_clusters = 160
        
        # Load pre-computed models and data
        self.load_models()
    
    def load_models(self):
        """Load pre-computed PCA, K-means, and TF-IDF data"""
        try:
            # Load PCA model
            self.pca = joblib.load("Image_descriptors/pca_model.pkl")
            
            # Load K-means model
            self.kmeans = joblib.load("Image_descriptors/kmeans_model.pkl")
            
            # Load descriptors and image paths
            data = np.load("Image_descriptors/descriptors.npz", allow_pickle=True)
            self.descriptors = data["descriptors"]
            self.image_paths = data["filenames"]
            
            # Load TF-IDF data
            tfidf_data = np.load("Image_descriptors/tfidf_data.npz", allow_pickle=True)
            self.tf_idf = tfidf_data["tf_idf"]
            self.idf = tfidf_data["idf"]
            
            print(f"Loaded {len(self.descriptors)} descriptors and {len(self.image_paths)} image paths")
            
        except FileNotFoundError as e:
            print(f"Error loading models: {e}")
            print("Please run the notebook first to generate the required files")
            raise
    
    def create_query_histogram(self, image_data):
        """Create histogram for uploaded image"""
        # Convert PIL image to OpenCV format
        pil_image = Image.open(io.BytesIO(image_data))
        img_array = np.array(pil_image)
        img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Extract SIFT features
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        if descriptors is None:
            print("No keypoints found in query image")
            return np.zeros(self.kmeans.n_clusters, dtype=float)
        
        # Apply PCA
        descriptors_reduced = self.pca.transform(descriptors)
        
        # Create histogram
        histogram = np.zeros(self.kmeans.n_clusters, dtype=int)
        cluster_assignments = self.kmeans.predict(descriptors_reduced)
        for idx in cluster_assignments:
            histogram[idx] += 1
        
        # Normalize
        histogram = histogram.astype(float)
        histogram /= np.sum(histogram) if np.sum(histogram) > 0 else 1
        
        return histogram
    
    def knn_search(self, query_histogram, k):
        """Perform KNN search using sequential method"""
        # Apply TF-IDF to query
        query = query_histogram * self.idf
        
        heap = []
        for i, hist in enumerate(self.tf_idf):
            dot = np.dot(query, hist)
            norm_query = np.linalg.norm(query)
            norm_hist = np.linalg.norm(hist)
            
            cosine_sim = 0
            if norm_query != 0 and norm_hist != 0:
                cosine_sim = dot / (norm_query * norm_hist)
            
            heapq.heappush(heap, (cosine_sim, self.image_paths[i]))
            
            if len(heap) > k:
                heapq.heappop(heap)
        
        # Return results in descending order
        top_k = sorted(heap, reverse=True)
        return top_k
    
    def search(self, image_data, k=5):
        """Main search function"""
        # Create histogram for query image
        query_histogram = self.create_query_histogram(image_data)
        
        # Perform KNN search
        results = self.knn_search(query_histogram, k)
        
        # Format results for frontend
        formatted_results = []
        for similarity, filename in results:
            formatted_results.append({
                "filename": f"{filename}.jpg",
                "similarity": float(similarity)
            })
        
        return formatted_results 