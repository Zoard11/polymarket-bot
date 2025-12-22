import json
import sys

def check_archive(file_path):
    print(f"Checking {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        print(f"Total Snapshots: {len(lines)}")
        if not lines:
            print("File is empty.")
            return

        # Check last snapshot
        last_line = lines[-1]
        data = json.loads(last_line)
        
        poly = data.get('poly_markets', [])
        kalshi = data.get('kalshi_markets', [])
        
        print(f"Last Snapshot Timestamp: {data.get('timestamp')}")
        print(f"Poly Markets Captured: {len(poly)}")
        print(f"Kalshi Markets Captured: {len(kalshi)}")
        
        if poly:
            sample = poly[0]
            m = sample.get('market', {})
            ob = sample.get('orderbook', {})
            print(f"Sample Poly Market: {m.get('slug')}")
            # Check structure
            # Normalized structure: orderbook -> tokens -> tid -> bids/asks
            # Or orderbook -> yes/no
            
            if 'tokens' in ob:
                print("Orderbook Structure: 'tokens' found (Good for multi-outcome)")
                tids = list(ob['tokens'].keys())
                print(f"Token IDs found: {len(tids)}")
                if tids:
                    first_book = ob['tokens'][tids[0]]
                    bids = first_book.get('bids', [])
                    asks = first_book.get('asks', [])
                    print(f"First Token Depth: {len(bids)} bids, {len(asks)} asks")
                    if bids: print(f"Sample Bid: {bids[0]}")
            
            if 'yes' in ob:
                print("Orderbook Structure: 'yes/no' found (Good for binary scanners)")

    except Exception as e:
        print(f"Error reading archive: {e}")

if __name__ == "__main__":
    check_archive("market_archive_vm.jsonl")
