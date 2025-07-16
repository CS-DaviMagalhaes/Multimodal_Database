import numpy as np
import librosa
import os
import joblib
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

def extract_audio_features(audio_path):
    """Extract features from a single audio file"""
    try:
        # Load audio with librosa
        y, sr = librosa.load(audio_path, sr=None)
        
        # Extract MFCC features
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfccs_mean = np.mean(mfccs, axis=1)
        mfccs_std = np.std(mfccs, axis=1)
        
        # Extract spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        
        # Extract zero crossing rate
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        
        # Extract chroma features
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Combine all features
        features = np.concatenate([
            mfccs_mean,
            mfccs_std,
            [np.mean(spectral_centroids), np.std(spectral_centroids)],
            [np.mean(spectral_rolloff), np.std(spectral_rolloff)],
            [np.mean(spectral_bandwidth), np.std(spectral_bandwidth)],
            [np.mean(zero_crossing_rate), np.std(zero_crossing_rate)],
            chroma_mean
        ])
        
        return features
        
    except Exception as e:
        print(f"Error processing {audio_path}: {e}")
        return None

def generate_audio_features(dataset_path="../data/audios_1000/"):
    """Generate features for all audio files in the dataset"""
    
    # Create audio_descriptors directory if it doesn't exist
    os.makedirs("audio_descriptors", exist_ok=True)
    
    # Get all audio files
    audio_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.aac']
    audio_files = []
    
    for filename in os.listdir(dataset_path):
        if any(filename.lower().endswith(ext) for ext in audio_extensions):
            audio_files.append(filename)
    
    print(f"Found {len(audio_files)} audio files")
    
    # Extract features for each audio file
    features_list = []
    filenames_list = []
    
    for filename in tqdm(audio_files, desc="Extracting audio features"):
        audio_path = os.path.join(dataset_path, filename)
        features = extract_audio_features(audio_path)
        
        if features is not None:
            features_list.append(features)
            filenames_list.append(filename)
    
    if not features_list:
        print("No features extracted. Check if audio files exist and are readable.")
        return
    
    # Convert to numpy arrays
    features_array = np.array(features_list)
    filenames_array = np.array(filenames_list)
    
    print(f"Successfully extracted features from {len(features_list)} audio files")
    print(f"Feature vector shape: {features_array.shape}")
    
    # Save features
    np.savez_compressed(
        "audio_descriptors/audio_features.npz",
        features=features_array,
        filenames=filenames_array
    )
    
    # Create and save scaler
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features_array)
    joblib.dump(scaler, "audio_descriptors/audio_scaler.pkl")
    
    print("Audio features saved successfully!")
    print(f"Files created:")
    print(f"- audio_descriptors/audio_features.npz")
    print(f"- audio_descriptors/audio_scaler.pkl")

if __name__ == "__main__":
    generate_audio_features() 