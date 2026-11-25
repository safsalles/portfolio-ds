"""Gera as figuras do README a partir de results/ (sem recalcular nada)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
TZ = "America/New_York"
OUT = ROOT / "docs"

cmp_ = pd.read_parquet(ROOT / "results" / "previsto_realizado.parquet")
wk = cmp_.set_index("hour").loc["2025-06-02":"2025-06-08"]
fig, ax = plt.subplots(figsize=(10, 3.6))
ax.plot(wk.index, wk["actual"], label="realizado / actual")
ax.plot(wk.index, wk["forecast"], label="previsto / forecast")
ax.set_title("Chamadas por hora, uma semana do ano de teste / calls per hour, one test-year week")
ax.legend(); fig.tight_layout(); fig.savefig(OUT / "previsto_realizado.png", dpi=130); plt.close(fig)

plan = pd.read_parquet(ROOT / "results" / "plano_pessoas.parquet")
loc = plan["hour"].dt.tz_convert(TZ)
wd = plan[loc.dt.day_of_week < 5].groupby(["scenario", loc[loc.dt.day_of_week < 5].dt.hour])["agents_scheduled"].mean().unstack(0)
fig, ax = plt.subplots(figsize=(10, 3.6))
wd.plot(ax=ax)
ax.set_title("Pessoas escaladas por hora do dia (dias úteis) / scheduled staff by hour (weekdays)")
ax.set_xlabel("hora / hour"); ax.set_ylabel("pessoas / people")
fig.tight_layout(); fig.savefig(OUT / "pessoas_por_hora.png", dpi=130); plt.close(fig)

c = pd.DataFrame(R["simulation"]["casos"])
c["caso"] = c["hora"] + " " + c["cenario"]
x = range(len(c))
fig, ax = plt.subplots(figsize=(10, 3.6))
w = 0.27
ax.bar([i - w for i in x], c["erlang"], w, label="Erlang C")
ax.bar(list(x), c["sim_exp"], w, label="simulação exp. / sim. exp.")
ax.bar([i + w for i in x], c["sim_lognormal"], w, label="simulação lognormal / sim. lognormal")
ax.set_xticks(list(x), c["caso"]); ax.set_ylim(0.7, 1.08); ax.legend(loc="upper center", ncol=3, frameon=False); ax.set_ylabel("nível de serviço / service level"); ax.text(0.01, 0.02, "eixo a partir de 0,70 / axis starts at 0.70", transform=ax.transAxes, fontsize=8, color="gray")
ax.set_title("Nível de serviço: Erlang C × simulação / service level: Erlang C vs simulation")
fig.tight_layout(); fig.savefig(OUT / "simulacao_erlang.png", dpi=130); plt.close(fig)
print("figuras ok")




# Ajuste das distribuições ao tempo de atendimento real (Technion), a partir de results.json
sys.path.insert(0, str(ROOT))
from app import logic  # noqa: E402
from src.distributions import DistSpec  # noqa: E402

defaults = logic.load_defaults(ROOT)
top3 = [(f"{x['rank']}. {x['name']}", DistSpec(x["name"], x["params"])) for x in defaults["fits"][:3]]
lognorm = next(x for x in defaults["fits"] if x["name"] == "lognormal")
top3.append((f"{lognorm['rank']}. lognormal (melhor erro quadrático / best squared error)", DistSpec("lognormal", lognorm["params"])))
fig = logic.plot_fits(defaults["service_values"], top3)
fig.axes[0].set_title("Atendimento real (Technion) e ajustes / real service time and fits")
fig.savefig(OUT / "atendimento_ajuste.png", dpi=130)
print("figura do ajuste ok")

