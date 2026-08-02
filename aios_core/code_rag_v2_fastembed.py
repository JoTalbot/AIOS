"""RAG v2 with fastembed support as alternative to sentence-transformers"""
try:
    from fastembed import TextEmbedding
    print("fastembed available")
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    embeddings = list(model.embed(["test hello world", "fix security bug"]))
    print(f"fastembed embeddings: {len(embeddings)} x {len(embeddings[0])}")
except Exception as e:
    print(f"fastembed failed: {e}")
    import traceback
    traceback.print_exc()
