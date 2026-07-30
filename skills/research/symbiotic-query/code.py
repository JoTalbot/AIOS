def remote_search(query, target_swarm):
    print(f'[SYMBIOSIS] Querying public memory of {target_swarm} for: "{query}"')
    # Simulation: return a relevant link from the partner
    return f"https://{target_swarm}.octopus-net.io/public/docs/merkle-optimization.md"

if __name__ == '__main__':
    link = remote_search('Merkle optimization', 'swarm-beta-99')
    print(f'Partner response: {link}')
