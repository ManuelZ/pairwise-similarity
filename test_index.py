# Standard Library imports
import os
import pickle 

# External imports
import tensorflow as tf
import faiss
import cv2
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Local imports
import siamese.config as config
from siamese.dataset import CommonMapFunction
from siamese.create_index import create_one_head_net

os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"


def display_query_results(im_query, images_paths, distances, indices, nrows=2, ncols=5):
    """ """

    assert nrows*ncols == config.N_RESULTS+1

    fig = plt.figure(figsize=(12, 8))  # w,h
    plt.subplot(nrows, ncols, 1)
    plt.imshow(im_query)
    plt.title("Query")

    for i, (dist, im_idx) in enumerate(zip(distances, indices)):
        image_path = images_paths[im_idx]
        im_pred = cv2.imread(str(image_path))
        im_pred = cv2.cvtColor(im_pred, cv2.COLOR_BGR2RGB)
        plt.subplot(nrows, ncols, i+1+1) # one corresponds to the query image
        plt.imshow(im_pred)
        plt.title(f"{dist:.3f}")
        plt.axis("off")

    plt.tight_layout()
    plt.show()


def query_index(embedding, index, index_type, n_results):
    """ """

    if index_type == "faiss":
        # Query the index with Faiss
        faiss.normalize_L2(embedding)
        distances, indices = index.search(embedding, n_results)
        indices = indices.ravel().tolist()
        distances = distances.ravel().tolist()
    
    elif index_type == "dict":
        embedding = embedding / np.linalg.norm(embedding)
        # similarities = cosine_similarity(index, embedding).ravel()

        distances = []
        for i in range(len(index)):
            d = np.linalg.norm(index[i,:] - embedding)
            distances.append(d)
        distances = np.array(distances)
        indices = distances.argsort()[:n_results]
        distances = distances[indices]

    return indices, distances


one_head_net = create_one_head_net(config.LOAD_MODEL_PATH)
map_fun = CommonMapFunction(config.IMAGE_SIZE)

images_paths = list(config.DATASET.rglob("*.jpg"))
query_paths = list(config.QUERY_DATASET.rglob("*.jpg"))      
print(f"There are {len(query_paths)} images for querying.")

# Read index
with open(config.MANUAL_INDEX_PATH, "rb") as f:
    index = pickle.load(f)
print(f"There are {len(index)} observations in the index")

#index = faiss.read_index(str(config.FAISS_INDEX_PATH))
# print(f"There are {index.ntotal} observations in the index")

for query_path in query_paths:
    
    # Load and preprocess image
    image = map_fun.decode_and_resize(str(query_path))
    
    # Add batch dimension
    image = tf.expand_dims(image, 0, name=None)
    
    # Extract embeddings
    embedding = one_head_net(image).numpy()

    indices, distances = query_index(embedding, index, "dict", config.N_RESULTS)

    # Display query and results
    im_query = cv2.imread(str(query_path))
    im_query = cv2.cvtColor(im_query, cv2.COLOR_BGR2RGB)
    display_query_results(im_query, images_paths, distances, indices)