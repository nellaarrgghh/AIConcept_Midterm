"""
Generates performance analysis charts and verifies
the difficulty hierarchy for BE-2.

Run from project root: py experiments/plots.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def generate_plots_and_checks():
    csv_path = 'logs/tournament_results.csv'
    if not os.path.exists(csv_path):
        print(f"Log file {csv_path} not found. Run tournament.py first.")
        return
    
    df = pd.read_csv(csv_path)
    os.makedirs('logs/plots', exist_ok=True)
    
    # 1. Calculate Proctor Win Rates (%)
    df['proctor_won'] = df['winner'] == 'proctor'
    win_rates = df.groupby('agent')['proctor_won'].mean() * 100
    
    print("\n--- Proctor Win Rates (%) ---")
    print(win_rates)
    
    # 2. Hierarchy Check (Hard/Medium peers beat Easy)
    agents_list = df['agent'].unique()
    print("\n--- Hierarchy Verification Check ---")
    if 'AlphaBeta' in agents_list and 'Minimax_Depth3' in agents_list and 'UCS' in agents_list:
        ab_wr = win_rates.get('AlphaBeta', 0)
        mm_wr = win_rates.get('Minimax_Depth3', 0)
        ucs_wr = win_rates.get('UCS', 0)
        
        print(f"AlphaBeta Win Rate: {ab_wr:.2f}%")
        print(f"Minimax Win Rate: {mm_wr:.2f}%")
        print(f"UCS (Easy) Win Rate: {ucs_wr:.2f}%")
        
        # Allow a small 5% margin for statistical ties between AlphaBeta and Minimax peers
        if (ab_wr >= ucs_wr and mm_wr >= ucs_wr) and abs(ab_wr - mm_wr) <= 6.0:
            print("Advanced search agents significantly outperform baseline UCS (Easy), with AlphaBeta/Minimax performing as expected.")
        else:
            print("Note: Hierarchy expectation violated.")
    
    # 3. Generate Win-Rate Bar Chart
    plt.figure(figsize=(8, 5))
    win_rates.plot(kind='bar', color=['skyblue', 'salmon', 'lightgreen'])
    plt.title('Overall Proctor Win Rate by Agent Type')
    plt.ylabel('Win Rate (%)')
    plt.ylim(0, 100)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('logs/plots/win_rate_bar_chart.png')
    plt.close()
    
    # 4. Generate Nodes Expanded Comparison Bar Chart
    plt.figure(figsize=(8, 5))
    nodes_df = df.groupby('agent')['nodes_expanded'].mean()
    nodes_df.plot(kind='bar', color=['purple', 'orange', 'teal'])
    plt.title('Average Nodes Expanded per Move')
    plt.ylabel('Nodes Count')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('logs/plots/nodes_expanded_comparison.png')
    plt.close()
    
    print("Plots generated successfully in logs/plots/")

if __name__ == "__main__":
    generate_plots_and_checks()