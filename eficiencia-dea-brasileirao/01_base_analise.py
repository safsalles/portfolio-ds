"""Monta a base de análise 2026: um jogador por linha, stats somadas e por 90 min, grupo de posição e lado.

Entrada (dados-fotmob/consolidado): br40/partidas_jogadores.csv.gz, br40/clubes_40.csv, perfil_jogadores.csv.gz
Saída: br40/base_analise_2026.csv
Grupos: Zagueiro (D/E/central), Lateral E/D, Volante, Meia atacante, Ponta E/D, Atacante, Goleiro.
"""
import sys
import pandas as pd

PASTA = sys.argv[1] if len(sys.argv) > 1 else "../../dados-fotmob/consolidado"
d = pd.read_csv(f"{PASTA}/br40/partidas_jogadores.csv.gz", low_memory=False)
clubes = pd.read_csv(f"{PASTA}/br40/clubes_40.csv")
perfil = pd.read_csv(f"{PASTA}/perfil_jogadores.csv.gz",
                     usecols=["id", "time_id", "posicao_principal", "pe_preferido", "nascimento", "idade", "valor_mercado_eur"])
# valor do elenco do clube = soma do valor de mercado dos jogadores do perfil que estão no clube
valor_clube = perfil[perfil.time_id.isin(clubes.time_id)].groupby("time_id").valor_mercado_eur.sum().rename("valor_elenco_clube_eur").reset_index()
perfil = perfil.drop(columns="time_id")

d = d[d.time_id.isin(clubes.time_id)].copy()  # só jogadores dos 40 clubes

# --- posição: posição principal do perfil -> grupo
GRUPO = {"Center Back": "Zagueiro", "Left Back": "Lateral E", "Left Wing-Back": "Lateral E",
         "Right Back": "Lateral D", "Right Wing-Back": "Lateral D",
         "Defensive Midfielder": "Volante", "Central Midfielder": "Volante",
         "Attacking Midfielder": "Meia atacante",
         "Left Winger": "Ponta E", "Left Midfielder": "Ponta E",
         "Right Winger": "Ponta D", "Right Midfielder": "Ponta D",
         "Striker": "Atacante", "Keeper": "Goleiro"}

# --- lado do zagueiro: contagem de jogos como titular nos lados D (33/34) e E (36/37); o central (35) não conta.
# Empate (ou sem jogos nos lados) -> pé preferido do perfil.
lado = d[d.titular & d.position_id_escalacao.isin([33, 34, 36, 37])]
lado = lado.assign(l=lado.position_id_escalacao.map({33: "D", 34: "D", 36: "E", 37: "E"}))
cont = lado.groupby(["jogador_id", "l"]).size().unstack(fill_value=0).reindex(columns=["D", "E"], fill_value=0)
lado_zag = pd.Series(pd.NA, index=cont.index, dtype="object")
lado_zag[cont.D > cont.E] = "D"
lado_zag[cont.E > cont.D] = "E"
lado_zag.name = "lado_zagueiro"
lado = lado_zag.to_frame()
lado["lado_origem"] = lado.lado_zagueiro.map(lambda x: "mais atuado" if pd.notna(x) else None)

# --- soma das stats
d["minutos"] = d.minutes_played
nao_somar = {"liga_id", "jogo_id", "data_utc", "time_id", "time", "jogador_id", "nome", "goleiro", "titular",
             "position_id_partida", "position_id_escalacao", "layout_y", "layout_x", "formacao", "usual_position",
             "rating_title", "Shotmap"}
cols = [c for c in d.columns if c not in nao_somar and pd.api.types.is_numeric_dtype(d[c])]
soma = d.groupby("jogador_id")[cols].sum(min_count=1)
soma["jogos"] = d.groupby("jogador_id").jogo_id.nunique()
soma["titular_jogos"] = d.groupby("jogador_id").titular.sum()
soma["rating_medio"] = d.groupby("jogador_id").rating_title.mean()
ult = d.sort_values("data_utc").groupby("jogador_id").agg(nome=("nome", "last"), time_id=("time_id", "last"), time=("time", "last"))
b = ult.join(soma).join(lado).reset_index().merge(perfil, left_on="jogador_id", right_on="id", how="left").drop(columns="id")
b = b.merge(clubes[["time_id", "divisao_2026"]], on="time_id", how="left")
b = b.merge(valor_clube, on="time_id", how="left")
b["grupo"] = b.posicao_principal.map(GRUPO)
# empate / só jogou de central -> pé preferido
zag = b.grupo == "Zagueiro"
pe = b.pe_preferido.map({"Right": "D", "Left": "E"})
sem = zag & b.lado_zagueiro.isna()
b.loc[sem, "lado_origem"] = pe[sem].map(lambda x: "pé preferido" if pd.notna(x) else "indefinido")
b.loc[sem, "lado_zagueiro"] = pe[sem]
b.loc[(b.grupo == "Zagueiro") & b.lado_zagueiro.notna(), "grupo_lado"] = "Zagueiro " + b.lado_zagueiro
b["grupo_lado"] = b.grupo_lado.fillna(b.grupo)

# --- taxas por 90 minutos (sufixo _p90)
for c in cols:
    if c != "minutos":
        b[c + "_p90"] = b[c] / b.minutos * 90

# --- filtro do artigo: metade superior em minutos (Q3 e Q4)
corte = b.minutos.median()
b["acima_mediana"] = b.minutos >= corte
b.to_csv(f"{PASTA}/br40/base_analise_2026.csv", index=False)
print("jogadores:", len(b), "| corte (mediana de minutos):", round(corte))
a = b[b.acima_mediana]
print(b.groupby("divisao_2026").valor_elenco_clube_eur.describe().round(0).to_string())
print(a.grupo.value_counts(dropna=False).to_string())
print(a[a.grupo == "Zagueiro"].groupby(["lado_zagueiro", "lado_origem"], dropna=False).size().to_string())
