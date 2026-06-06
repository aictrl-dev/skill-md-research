import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# (exp, nodes, REAL F2, topology, color)
pts = [
    ("exp-007", 5, 0.198, "proof-obligation", "#d62728"),
    ("exp-003", 5, 0.433, "5-lens union", "#1f77b4"),
    ("exp-008", 10, 0.407, "10-lens union", "#ff7f0e"),
    ("exp-009", 15, 0.420, "15-lens union", "#ff7f0e"),
    ("exp-010", 15, 0.523, "5x3 independent", "#2ca02c"),
    ("exp-011", 15, 0.581, "5x3 DIRECTED", "#9467bd"),
]
fig, ax = plt.subplots(figsize=(9,6))
seen=set()
for exp,n,f2,topo,c in pts:
    lab = topo if topo not in seen else None; seen.add(topo)
    ax.scatter(n, f2, s=130, color=c, zorder=3, label=lab, edgecolor="black", linewidth=0.5)
    ax.annotate(f"{exp}\n{f2:.3f}", (n,f2), textcoords="offset points", xytext=(8,6), fontsize=8)

# reference lines (different model / full-set basis — annotate, not same axis)
ax.axhline(0.665, ls="--", color="gray", lw=1)
ax.text(15.4, 0.665, "Opus 1-pass (full-set, circular P) 0.665", va="center", fontsize=7, color="gray")
ax.axhline(0.333, ls=":", color="gray", lw=1)
ax.text(15.4, 0.333, "Haiku4.5 1-pass (full-set) 0.333", va="center", fontsize=7, color="gray")

ax.set_xlabel("Gemma calls (AI nodes in DAG)")
ax.set_ylabel("REAL-set F2 (recall-weighted, real-bug subset)")
ax.set_title("cr-skill-workflow: nodes vs F2 — topology matters more than count")
ax.set_xticks([1,5,10,15]); ax.set_xlim(0,22); ax.set_ylim(0.15,0.72)
ax.grid(True, alpha=0.3); ax.legend(loc="lower right", fontsize=8, title="topology")
fig.tight_layout(); fig.savefig("analysis/nodes-vs-f2.png", dpi=130)
print("wrote analysis/nodes-vs-f2.png")
