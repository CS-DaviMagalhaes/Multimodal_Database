import cv2 
import matplotlib.pyplot as plt
import os

import os
import cv2

dataset_path = "../data/fashion_small_100/"
extracted = []

for filename in os.listdir(dataset_path):  # Iterar sobre todas las imágenes de la carpeta
    file_path = os.path.join(dataset_path, filename)
    
    if os.path.isfile(file_path):
        img = cv2.imread(file_path) 
        if img is None:
            print(f"No se pudo leer la imagen: {file_path}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Convertir a escala de grises
        sift = cv2.SIFT_create()  # O cv2.xfeatures2d.SIFT_create() 

        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        extracted.append((file_path, keypoints, descriptors))  

