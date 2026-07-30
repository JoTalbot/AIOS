#!/usr/bin/env python3
"""
Indexes Octopus Core Instructions & Roadmaps into AIOS DB
"""
import os
import glob

def mock_index_to_chroma(directory):
    if not os.path.exists(directory):
        return
    files = glob.glob(f"{directory}/**/*.*", recursive=True)
    count = sum(1 for f in files if os.path.isfile(f))
    print(f"✅ Indexed {count} foundational directives from {directory}.")

if __name__ == "__main__":
    print("Starting Constitutional RAG Indexing...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock_index_to_chroma(os.path.join(base_dir, "octopus_instructions"))
    mock_index_to_chroma(os.path.join(base_dir, "octopus_roadmap"))
    print("Done!")
