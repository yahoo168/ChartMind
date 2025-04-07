import numpy as np

def cosine_similarity(vector1:list, vector2:list):
    return np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))

def euclidean_distance(vector1:list, vector2:list):
    return np.linalg.norm(np.array(vector1) - np.array(vector2))

def manhattan_distance(vector1:list, vector2:list):
    return np.sum(np.abs(np.array(vector1) - np.array(vector2)))