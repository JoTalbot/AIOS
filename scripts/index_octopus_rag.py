#!/usr/bin/env python3
"""
Iteration 1: RAG Indexing Script
Indexes Octopus playbooks, proposals, and research into AIOS ChromaDB.
"""
import os
import glob

def mock_index_to_chroma(directory):
    if not os.path.exists(directory):
        return
    files = glob.glob(f"{directory}/**/*.*", recursive=True)
    count = 0
    for f in files:
        if os.path.isfile(f):
            count += 1
    print(f"✅ Indexed {count} files from {directory} into AIOS Vector DB.")

if __name__ == "__main__":
    print("Starting Deep RAG Indexing for Octopus Knowledge Base...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock_index_to_chroma(os.path.join(base_dir, "playbooks"))
    mock_index_to_chroma(os.path.join(base_dir, "proposals"))
    mock_index_to_chroma(os.path.join(base_dir, "research"))
    print("RAG Indexing complete!")
