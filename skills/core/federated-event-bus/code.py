import json

def publish_event(event_type, data):
    event = {
        'type': event_type,
        'data': data,
        'bus': 'nostr_federation_v1'
    }
    print(f'[FEDERATION] Publishing to Nostr: {json.dumps(event)}')
    # Future: real nostr-relay-client call

if __name__ == '__main__':
    publish_event('node_up', {'id': 'parent'})
