from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-base-en-v1.5")
vector_dim = model.get_sentence_embedding_dimension()


def get_embedding(text: str):
    return model.encode(text).tolist()
