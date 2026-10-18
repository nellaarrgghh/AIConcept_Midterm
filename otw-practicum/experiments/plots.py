"""
Generates analysis charts from tournament and pruning study logs (experiments/plots.py).

Produces in logs/plots/:
  (a) win_rate_by_agent_student.png: Win rate by Proctor agent and student type
  (b) pruning_study_nodes_vs_depth.png: Nodes expanded vs depth (log y-axis) for Minimax and fixed-depth Alpha-Beta
  (c) nodes_expanded_comparison.png: Existing nodes expanded per move on log y-axis with full title & caption
  (d) depth_reached_comparison.png: Average depth reached by time-limited Alpha-Beta vs Minimax fixed depth
"""

import os
import sys
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def generate_all_plots():
    os.makedirs("logs/plots", exist_ok=True)
    tournament_csv = "logs/tournament_results.csv"
    pruning_csv = "logs/pruning_study.csv"

    if not os.path.exists(tournament_csv):
        print(f"Error: {tournament_csv} not found. Run tournament.py first.")
        return

    df = pd.read_csv(tournament_csv)
    df["proctor_won"] = df["winner"] == "proctor"

    # -------------------------------------------------------------------------
    # (a) Win rate by Proctor agent and student type
    # -------------------------------------------------------------------------
    plt.figure(figsize=(9, 5))
    win_summary = df.groupby(["agent", "student_type"])["proctor_won"].mean().unstack() * 100
    ax = win_summary.plot(kind="bar", figsize=(9, 5), colormap="viridis", edgecolor="black")
    plt.title("Proctor Win Rate by Agent and Student Type (Turn Limit T=6)", fontsize=13, fontweight="bold")
    plt.ylabel("Proctor Win Rate (%)", fontsize=11)
    plt.xlabel("Proctor Agent", fontsize=11)
    plt.ylim(0, 105)
    plt.xticks(rotation=0)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.legend(title="Student Type")
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.annotate(f"{height:.1f}%",
                        (p.get_x() + p.get_width() / 2., height + 1.5),
                        ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plot_a_path = "logs/plots/win_rate_by_agent_student.png"
    plt.savefig(plot_a_path, dpi=150)
    plt.close()
    print(f"Saved: {plot_a_path}")

    # Also keep win_rate_bar_chart.png for overall win rates
    plt.figure(figsize=(8, 5))
    overall_win = df.groupby("agent")["proctor_won"].mean() * 100
    overall_win.plot(kind="bar", color=["#4c72b0", "#dd8452", "#55a868"], edgecolor="black")
    plt.title("Overall Proctor Win Rate by Agent Type", fontsize=13, fontweight="bold")
    plt.ylabel("Win Rate (%)", fontsize=11)
    plt.xlabel("Proctor Agent", fontsize=11)
    plt.ylim(0, 105)
    plt.xticks(rotation=0)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plot_legacy_path = "logs/plots/win_rate_bar_chart.png"
    plt.savefig(plot_legacy_path, dpi=150)
    plt.close()
    print(f"Saved: {plot_legacy_path}")

    # -------------------------------------------------------------------------
    # (b) Nodes expanded vs. depth for Minimax and fixed-depth Alpha-Beta (log y-axis)
    # -------------------------------------------------------------------------
    if os.path.exists(pruning_csv):
        df_prune = pd.read_csv(pruning_csv)
        plt.figure(figsize=(8, 5))
        for agent_name in ["Minimax", "AlphaBeta"]:
            sub = df_prune[df_prune["agent"] == agent_name]
            plt.plot(sub["depth"], sub["avg_nodes_expanded"], marker="o", linewidth=2, label=agent_name)

        plt.yscale("log")
        plt.title("Nodes Expanded vs. Depth: Minimax vs. Fixed-Depth Alpha-Beta", fontsize=12, fontweight="bold")
        plt.xlabel("Search Depth", fontsize=11)
        plt.ylabel("Average Nodes Expanded (log scale)", fontsize=11)
        plt.xticks([1, 2, 3, 4, 5])
        plt.grid(True, which="both", linestyle="--", alpha=0.5)
        plt.legend(fontsize=11)
        plt.tight_layout()
        plot_b_path = "logs/plots/pruning_study_nodes_vs_depth.png"
        plt.savefig(plot_b_path, dpi=150)
        plt.close()
        print(f"Saved: {plot_b_path}")

    # -------------------------------------------------------------------------
    # (c) Nodes expanded per move chart on log y-axis with full title & caption
    # -------------------------------------------------------------------------
    plt.figure(figsize=(8, 6))
    nodes_df = df.groupby("agent")["nodes_expanded"].mean()
    # Clamp minimum value to 1 to plot cleanly on log scale
    nodes_df_plot = nodes_df.apply(lambda x: max(1, x))
    ax = nodes_df_plot.plot(kind="bar", color=["#4c72b0", "#dd8452", "#55a868"], edgecolor="black")
    plt.yscale("log")
    plt.title("Nodes expanded per move (Alpha-Beta uses iterative deepening, 1 s budget)", fontsize=12, fontweight="bold")
    plt.ylabel("Average Nodes Expanded (log scale)", fontsize=11)
    plt.xlabel("Proctor Agent", fontsize=11)
    plt.xticks(rotation=0)
    plt.grid(axis="y", which="both", linestyle="--", alpha=0.5)

    caption_text = (
        "Note: Search depths differ significantly between agents.\n"
        "Alpha-Beta uses iterative deepening (1.0 s budget) capped at remaining game plies,\n"
        "whereas Minimax is fixed at depth 3. UCS is a single-agent shortest-path algorithm (not a game-tree search)."
    )
    plt.figtext(0.5, -0.05, caption_text, wrap=True, horizontalalignment="center", fontsize=9, style="italic")
    plt.tight_layout()
    plot_c_path = "logs/plots/nodes_expanded_comparison.png"
    plt.savefig(plot_c_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {plot_c_path}")

    # -------------------------------------------------------------------------
    # (d) Average depth reached by time-limited Alpha-Beta next to Minimax fixed depth
    # -------------------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    tree_agents = df[df["agent"].isin(["Minimax_Depth3", "AlphaBeta"])]
    avg_depth = tree_agents.groupby("agent")["depth_reached"].mean()

    ax = avg_depth.plot(kind="bar", color=["#dd8452", "#55a868"], edgecolor="black", width=0.4)
    plt.title("Average Depth Reached: Fixed-Depth Minimax vs. Time-Limited Alpha-Beta", fontsize=12, fontweight="bold")
    plt.ylabel("Search Depth", fontsize=11)
    plt.xlabel("Agent", fontsize=11)
    plt.xticks(rotation=0)
    plt.ylim(0, max(avg_depth.values) * 1.25)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f"Depth {height:.1f}",
                    (p.get_x() + p.get_width() / 2., height + 0.3),
                    ha="center", va="bottom", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plot_d_path = "logs/plots/depth_reached_comparison.png"
    plt.savefig(plot_d_path, dpi=150)
    plt.close()
    print(f"Saved: {plot_d_path}")

    print("\nAll plots generated and saved successfully to logs/plots/.")


if __name__ == "__main__":
    generate_all_plots()