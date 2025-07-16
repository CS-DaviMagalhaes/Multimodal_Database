import os
import pickle
import math
import re
from collections import defaultdict, Counter
import heapq
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Ensure NLTK resources are available
try:
    stop_words = set(stopwords.words('english'))
except LookupError:
    import nltk
    nltk.download('stopwords')
    stop_words = set(stopwords.words('english'))

stemmer = PorterStemmer()

def preprocess_text(row):
    text = f"{row.get('case_id', '')} {row.get('case_title', '')} {row.get('case_outcome', '')} {row.get('case_text', '')}".lower()
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = text.split()
    tokens = [stemmer.stem(t) for t in tokens if t not in stop_words]
    return tokens

def query_from_blocks(query, index_dir="text_descriptors/index_blocks", k=5):
    with open(os.path.join(index_dir, "norms.pkl"), "rb") as f:
        norms = pickle.load(f)
    with open(os.path.join(index_dir, "df_counter.pkl"), "rb") as f:
        df_counter = pickle.load(f)

    query_tokens = preprocess_text({'case_id': '', 'case_title': '', 'case_outcome': '', 'case_text': query})
    tf = Counter(query_tokens)
    scores = defaultdict(float)
    query_len = 0
    total_docs = len(norms)

    block_files = [f for f in os.listdir(index_dir) if f.startswith("block_") and f.endswith(".pkl")]
    block_files.sort()

    for term, freq in tf.items():
        tf_weight = 1 + math.log10(freq)
        df = df_counter.get(term, 1)
        idf = math.log10(total_docs / df)
        w_tq = tf_weight * idf
        query_len += w_tq ** 2

        for file in block_files:
            with open(os.path.join(index_dir, file), "rb") as f:
                block_index = pickle.load(f)
                if term in block_index:
                    for doc_id, w_td in block_index[term]:
                        scores[doc_id] += w_td * w_tq

    query_norm = math.sqrt(query_len)
    for doc_id in scores:
        scores[doc_id] /= (norms[doc_id] * query_norm)

    return heapq.nlargest(k, scores.items(), key=lambda x: x[1]) 