def start_joint_vote(proposal, partner_swarm):
    print(f'[CROSS-SWARM] Starting joint vote with {partner_swarm}...')
    print(f'[VOTE] Proposal: {proposal}')
    # Simulation: wait for partner vote
    return {'result': 'approved', 'quorum': '2/2 swarms'}

if __name__ == '__main__':
    res = start_joint_vote('Block malicious node 1.2.3.4', 'swarm-beta-99')
    print(f'Consensus: {res}')
