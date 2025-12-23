#!/usr/bin/env python3
"""
Analysis script for Polymarket Maker Scanner logs.
Analyzes opportunities found, execution patterns, and profitability.
"""

import json
import re
from datetime import datetime
from collections import defaultdict, Counter
import config

def parse_opportunities_log(filepath):
    """Parse opportunities.log to extract all spread opportunities."""
    opportunities = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the separator line
    entries = content.split('----------------------------------------')
    
    for entry in entries:
        if '[MAKER-GEN]' not in entry:
            continue
            
        try:
            # Extract timestamp
            time_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', entry)
            timestamp = time_match.group(1) if time_match else None
            
            # Extract market
            market_match = re.search(r'Market: (.+)', entry)
            market = market_match.group(1).strip() if market_match else None
            
            # Extract bids
            bids_match = re.search(r'Current Bids: YES ([\d.]+) \+ NO ([\d.]+) = ([\d.]+)', entry)
            if bids_match:
                yes_bid = float(bids_match.group(1))
                no_bid = float(bids_match.group(2))
                total = float(bids_match.group(3))
            else:
                continue
            
            # Extract profit
            profit_match = re.search(r'Spread Profit: ([\d.]+)%', entry)
            profit_pct = float(profit_match.group(1)) if profit_match else None
            
            # Extract link
            link_match = re.search(r'Link: (.+)', entry)
            link = link_match.group(1).strip() if link_match else None
            
            opportunities.append({
                'timestamp': timestamp,
                'market': market,
                'yes_bid': yes_bid,
                'no_bid': no_bid,
                'total_cost': total,
                'profit_pct': profit_pct,
                'link': link
            })
        except Exception as e:
            continue
    
    return opportunities

def analyze_opportunities(opportunities):
    """Generate statistics from opportunities."""
    if not opportunities:
        return None
    
    stats = {
        'total_count': len(opportunities),
        'unique_markets': len(set(o['market'] for o in opportunities)),
        'avg_profit_pct': sum(o['profit_pct'] for o in opportunities) / len(opportunities),
        'max_profit_pct': max(o['profit_pct'] for o in opportunities),
        'min_profit_pct': min(o['profit_pct'] for o in opportunities),
        'profit_distribution': Counter(),
        'top_markets': Counter(),
        'hourly_distribution': Counter()
    }
    
    for opp in opportunities:
        # Profit buckets
        if opp['profit_pct'] >= 2.0:
            stats['profit_distribution']['2%+'] += 1
        elif opp['profit_pct'] >= 1.5:
            stats['profit_distribution']['1.5-2%'] += 1
        elif opp['profit_pct'] >= 1.0:
            stats['profit_distribution']['1-1.5%'] += 1
        else:
            stats['profit_distribution']['<1%'] += 1
        
        # Top markets
        stats['top_markets'][opp['market']] += 1
        
        # Hourly distribution
        if opp['timestamp']:
            hour = opp['timestamp'].split(':')[0]
            stats['hourly_distribution'][hour] += 1
    
    return stats

def main():
    print("=" * 80)
    print("POLYMARKET MAKER SCANNER - 9 HOUR ANALYSIS")
    print("=" * 80)
    
    # Parse opportunities log
    print("\nParsing opportunities.log...")
    try:
        opportunities = parse_opportunities_log('opportunities.log')
        print(f"Found {len(opportunities)} opportunities")
    except FileNotFoundError:
        print("opportunities.log not found")
        return
    
    # Analyze
    print("\nAnalyzing data...")
    stats = analyze_opportunities(opportunities)
    
    if not stats:
        print("No data to analyze")
        return
    
    # Report
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total Opportunities Found: {stats['total_count']:,}")
    print(f"Unique Markets: {stats['unique_markets']}")
    print(f"Average Profit: {stats['avg_profit_pct']:.2f}%")
    print(f"Max Profit: {stats['max_profit_pct']:.2f}%")
    print(f"Min Profit: {stats['min_profit_pct']:.2f}%")
    
    print("\n" + "-" * 80)
    print("PROFIT DISTRIBUTION")
    print("-" * 80)
    for bucket, count in sorted(stats['profit_distribution'].items(), reverse=True):
        pct = (count / stats['total_count']) * 100
        print(f"{bucket:10s}: {count:5d} ({pct:5.1f}%)")
    
    print("\n" + "-" * 80)
    print("TOP 10 MARKETS (Most Frequent Opportunities)")
    print("-" * 80)
    for market, count in stats['top_markets'].most_common(10):
        print(f"{count:3d}x - {market[:70]}")
    
    print("\n" + "-" * 80)
    print("HOURLY DISTRIBUTION")
    print("-" * 80)
    for hour in sorted(stats['hourly_distribution'].keys()):
        count = stats['hourly_distribution'][hour]
        # Shorter bars: divisor increased to 100
        bar = '#' * (count // 100)
        print(f"{hour}:00 - {count:4d} {bar}")
    
    # Calculate theoretical profit
    print("\n" + "=" * 80)
    print("THEORETICAL PROFIT ANALYSIS (if all executed)")
    print("=" * 80)
    
    trade_size = getattr(config, 'MAKER_TRADE_SIZE_USD', 200)  # Use config
    fee_pct = getattr(config, 'FEE_PCT', 0.5) / 100.0         # 0.5% -> 0.005
    
    total_gross_profit = sum(o['profit_pct'] / 100 * trade_size for o in opportunities)
    # Realistic Fee impact: We trade twice (YES and NO), so fee is applied twice to half the size each, or once to total size
    total_fees = stats['total_count'] * trade_size * fee_pct * 2
    total_net_profit = total_gross_profit - total_fees
    
    print(f"Trade Size: ${trade_size}")
    print(f"Total Opportunities: {stats['total_count']}")
    print(f"Total Fees (${fee_pct*2*100:.1f}% per cycle): ${total_fees:,.2f}")
    print(f"Theoretical Gross Profit: ${total_gross_profit:,.2f}")
    print(f"Realistic Net Profit: ${total_net_profit:,.2f}")
    print(f"Average Net Profit per Trade: ${total_net_profit / stats['total_count']:.2f}")
    
    # Estimate with execution rate
    execution_rates = [0.1, 0.25, 0.5]
    print("\n" + "-" * 80)
    print("NET PROFIT ESTIMATES (by execution rate)")
    print("-" * 80)
    for rate in execution_rates:
        executed = int(stats['total_count'] * rate)
        net_profit = total_net_profit * rate
        print(f"{rate*100:3.0f}% execution ({executed:4d} trades): ${net_profit:8,.2f}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
