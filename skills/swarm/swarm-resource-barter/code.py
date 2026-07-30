def evaluate_deal(offer, demand):
    print(f'[BARTER] Evaluating trade: {offer} for {demand}...')
    # Logic: 1 hour of Whisper CPU = 1GB of S3 Storage
    if offer == '1h_whisper' and demand == '1GB_storage':
        return True
    return False

if __name__ == '__main__':
    deal = evaluate_deal('1h_whisper', '1GB_storage')
    print(f'Trade Authorized: {deal}')
