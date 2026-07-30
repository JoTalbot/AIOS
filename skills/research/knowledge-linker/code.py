import os
import json

LOGS_DIR = '/root/agents/-Octopus/logs'
TRANSCRIPTS_DIR = '/mnt/swarm/google_drive_calls/Calls/'

def link_context():
    # Simple keyword-based linking between logs and transcripts
    keywords = ['Octopus', 'AWS', 'Merkle', 'People']
    links = []
    
    # Just a proof of concept for now
    for log in os.listdir(LOGS_DIR):
        if log.endswith('.md'):
            links.append({'source': log, 'target': 'transcripts_link', 'type': 'context'})
    
    print(f'Processed {len(links)} log files for linking.')
    return links

if __name__ == '__main__':
    link_context()
