"""Gera planilha/dimensionamento_equipe.xlsx: calculadora de equipe (Erlang C) com fórmulas, sem macro.

Precisa dos parquets de results/. Uso: python scripts/gerar_planilha.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter as col

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gerar_pagina import TZ, build_data  # noqa: E402

OUT = ROOT / "planilha" / "dimensionamento_equipe.xlsx"
MAX_N = 400  # maior equipe calculada
MAX_ERLANGS = 250  # carga máxima aceita (chamadas/h x minutos / 60)
FIRST = 6  # primeira linha de Cálculos (N = 1)
LAST = FIRST + MAX_N - 1
PAGE = "https://safsalles.github.io/portfolio-ds/dimensionamento-equipe/site/"
REPO = "https://github.com/safsalles/portfolio-ds/tree/main/dimensionamento-equipe"

NAVY = "1F3A5F"
F = lambda **k: Font(name="Arial", **k)  # noqa: E731
INPUT = PatternFill("solid", fgColor="FFF2B3")
HEAD = PatternFill("solid", fgColor=NAVY)
BIG = PatternFill("solid", fgColor="EAF2FD")
LINE = Side(style="thin", color="D0D0CA")
BOX = Border(left=LINE, right=LINE, top=LINE, bottom=LINE)


def sheet(ws, title: str, widths: list[float]):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[col(i)].width = w
    ws["B2"] = title
    ws["B2"].font = F(size=16, bold=True, color=NAVY)
    ws.sheet_view.showGridLines = False


def put(ws, ref, value, fmt=None, bold=False, size=11, color="000000", fill=None, box=False, wrap=False):
    c = ws[ref]
    c.value = value
    c.font = F(bold=bold, size=size, color=color)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if box:
        c.border = BOX
    if wrap:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    return c


def header(ws, row: int, first_col: int, names: list[str]):
    for i, n in enumerate(names):
        c = put(ws, f"{col(first_col + i)}{row}", n, bold=True, color="FFFFFF", fill=HEAD, box=True)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def line_chart(title, y_title, data_ref, cats, anchor, ws, width=22, height=8):
    ch = LineChart()
    ch.title, ch.width, ch.height = title, width, height
    ch.roundedCorners = False
    ch.add_data(data_ref, titles_from_data=True)
    ch.set_categories(cats)
    ch.y_axis.title = y_title
    ch.title.overlay = False
    ch.y_axis.title.overlay = False
    ch.legend.position = "b"
    ch.legend.overlay = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    for s in ch.series:
        s.smooth = False
    ws.add_chart(ch, anchor)


def start(ws):
    sheet(ws, "Quantas pessoas são necessárias, hora a hora?", [3, 100])
    rows = [
        ("Como usar", True),
        ("1. Abra a aba Calculadora e preencha as células amarelas.", False),
        ("2. Veja em Contratar ou demitir o que muda com mais ou menos gente.", False),
        ("3. Veja em Escala do dia quantas pessoas cada hora de um dia útil pede.", False),
        ("", False),
        ("Aviso: a equipe, o tempo de atendimento, a meta e a folga são fictícios. É um cenário didático.", True),
        ("As chegadas vêm de dados reais do NYC 311 (NYC Open Data), chamadas de telefone de 2024 e 2025.", False),
        ("O cálculo é o Erlang C: supõe chegadas aleatórias, atendimento com distribuição exponencial e ninguém desistindo da fila.", False),
        ("A simulação com outras distribuições e a comparação com um call center real não estão aqui: veja a página e o código.", False),
    ]
    for i, (text, bold) in enumerate(rows, 4):
        put(ws, f"B{i}", text, bold=bold, wrap=True)
    for i, (label, url) in enumerate((("Abrir a página com os gráficos", PAGE), ("Abrir o código no GitHub", REPO)), 14):
        c = put(ws, f"B{i}", label, color="1155CC")
        c.hyperlink = url


def calculator(ws, default_calls: float, fitted_minutes: float):
    sheet(ws, "Calculadora de equipe", [3, 46, 18, 3, 60])
    put(ws, "B4", "Preencha as células amarelas", bold=True)
    inputs = [
        (5, "Chamadas por hora", default_calls, "#,##0", f"Valor inicial: mediana das horas úteis (9h-17h). Limite: carga de até {MAX_ERLANGS} erlangs."),
        (6, "Minutos por atendimento", 6, "0.0", "Premissa fictícia. A página e o app usam " + f"{fitted_minutes:.1f}".replace(".", ",") + " minutos (tempos reais de um banco), por isso lá a equipe é menor."),
        (7, "Atender em até (segundos)", 20, "0", "Meta de espera."),
        (8, "... em pelo menos esta fração das chamadas", 0.8, "0%", "Ex.: 80% (meta 80/20)."),
        (9, "Folga para pausas e ausências", 0.3, "0%", "Premissa fictícia."),
    ]
    for r, label, value, fmt, note in inputs:
        put(ws, f"B{r}", label, box=True)
        put(ws, f"C{r}", value, fmt, color="0000FF", fill=INPUT, box=True).protection = Protection(locked=False)
        put(ws, f"E{r}", note, color="52514E", size=9, wrap=True)
    ok = (f"IFERROR(AND(ISNUMBER(C5),ISNUMBER(C6),ISNUMBER(C7),ISNUMBER(C8),ISNUMBER(C9),C5>=0,C6>0,C7>=0,"
          f"C8>0,C8<1,C9>=0,C9<1,C5*C6/60<={MAX_ERLANGS}),FALSE)")
    put(ws, "B11", f'=IF({ok},"Resultado","Confira as células amarelas: há um valor vazio, negativo ou acima do limite.")', bold=True)
    found = f"ISNUMBER('Cálculos'!B2)"
    results = [
        (13, "Pessoas presentes necessárias", f"=IF({ok},IF(C5=0,0,IF({found},'Cálculos'!B2,\"acima de {MAX_N}\")),\"-\")", "#,##0", True),
        (14, "Pessoas a escalar (com a folga)", "=IF(ISNUMBER(C13),ROUNDUP(ROUND(C13/(1-C9),9),0),\"-\")", "#,##0", True),
        (15, "Carga (erlangs): pessoas ocupadas o tempo todo", f"=IF({ok},C5*C6/60,\"-\")", "0.00", False),
        (16, "Chance de uma chamada esperar", f"=IF(AND(ISNUMBER(C13),N(C13)>0),INDEX('Cálculos'!C{FIRST}:C{LAST},C13),IF(C13=0,0,\"-\"))", "0.0%", False),
        (17, "Atendidas dentro da meta de espera", f"=IF(AND(ISNUMBER(C13),N(C13)>0),INDEX('Cálculos'!D{FIRST}:D{LAST},C13),IF(C13=0,1,\"-\"))", "0.0%", False),
        (18, "Espera média (segundos)", f"=IF(AND(ISNUMBER(C13),N(C13)>0),INDEX('Cálculos'!E{FIRST}:E{LAST},C13),IF(C13=0,0,\"-\"))", "0.0", False),
    ]
    for r, label, formula, fmt, big in results:
        put(ws, f"B{r}", label, box=True, bold=big, fill=BIG if big else None)
        c = put(ws, f"C{r}", formula, fmt, bold=big, size=20 if big else 11, box=True, fill=BIG if big else None)
        c.alignment = Alignment(horizontal="right")
    put(ws, "B20", "Erlang C: atendimento com distribuição exponencial, chegadas aleatórias e ninguém desistindo. "
        "Na vida real há desistências e pausas: use o resultado para comparar cenários, não como promessa de espera.",
        size=9, color="52514E", wrap=True)
    ws.merge_cells("B20:E20")
    ws.row_dimensions[20].height = 30
    for r in range(5, 10):
        ws.row_dimensions[r].height = 26


def calculations(ws, hours: int = 24):
    ws["A1"] = "Carga (erlangs)"
    ws["B1"] = f"=IFERROR(MAX(0,MIN(Calculadora!C5*Calculadora!C6/60,{MAX_ERLANGS})),0)"
    ws["A2"] = "Pessoas necessárias"
    ws["B2"] = f"=IFERROR(INDEX(A{FIRST}:A{LAST},MATCH(1,F{FIRST}:F{LAST},0)),\"nenhuma\")"
    for i, n in enumerate(["Pessoas", "Erlang B", "Chance de esperar", "Dentro da meta", "Espera média (s)", "Atinge"], 1):
        ws.cell(FIRST - 1, i, n)
    wait, target, aht = "Calculadora!$C$7", "Calculadora!$C$8", "(Calculadora!$C$6*60)"
    for k in range(MAX_N):
        r = FIRST + k
        prev = "1" if k == 0 else f"B{r - 1}"
        ws[f"A{r}"] = k + 1
        ws[f"B{r}"] = f"=$B$1*{prev}/(A{r}+$B$1*{prev})"
        ws[f"C{r}"] = f"=IF(A{r}<=$B$1,1,B{r}/(1-($B$1/A{r})*(1-B{r})))"
        ws[f"D{r}"] = f"=IFERROR(IF(A{r}<=$B$1,0,1-C{r}*EXP(-(A{r}-$B$1)*{wait}/{aht})),0)"
        ws[f"E{r}"] = f"=IFERROR(IF(A{r}<=$B$1,\"fila sem controle\",C{r}*{aht}/(A{r}-$B$1)),\"-\")"
        ws[f"F{r}"] = f"=IF(AND(A{r}>$B$1,D{r}>={target}),1,0)"
    # uma dupla de colunas por hora do dia (Escala do dia): Erlang B e "atinge a meta"
    for h in range(hours):
        b, m = col(8 + 2 * h), col(9 + 2 * h)
        load = f"{b}$3"
        ws[f"{b}2"] = f"{h}h"
        ws[f"{b}3"] = f"=IFERROR(MIN('Escala do dia'!B{5 + h}*Calculadora!$C$6/60,{MAX_ERLANGS}),0)"
        for k in range(MAX_N):
            r = FIRST + k
            prev = "1" if k == 0 else f"{b}{r - 1}"
            ws[f"{b}{r}"] = f"={load}*{prev}/($A{r}+{load}*{prev})"
            ws[f"{m}{r}"] = (f"=IFERROR(IF($A{r}<={load},0,IF(1-({b}{r}/(1-({load}/$A{r})*(1-{b}{r})))"
                             f"*EXP(-($A{r}-{load})*{wait}/{aht})>={target},1,0)),0)")
    ws.sheet_state = "hidden"


def hire_fire(ws):
    sheet(ws, "O que muda ao contratar ou demitir", [3, 22, 12, 22, 20, 14])
    put(ws, "B3", "Parte da equipe necessária calculada na aba Calculadora.", color="52514E", size=9)
    header(ws, 4, 2, ["Mudança", "Pessoas", "Dentro da meta", "Espera média (s)", "Meta"])
    for i, d in enumerate(range(-5, 6)):
        r = 5 + i
        label = "Equipe necessária" if d == 0 else (f"Contratar {d}" if d > 0 else f"Demitir {-d}")
        put(ws, f"B{r}", label, box=True, bold=d == 0)
        put(ws, f"C{r}", f'=IF(ISNUMBER(Calculadora!$C$13),MAX(0,Calculadora!$C$13+({d})),"-")', "#,##0", box=True, bold=d == 0)
        put(ws, f"D{r}", f"=IFERROR(INDEX('Cálculos'!$D${FIRST}:$D${LAST},C{r}),0)", "0.0%", box=True, bold=d == 0)
        put(ws, f"E{r}", f"=IFERROR(INDEX('Cálculos'!$E${FIRST}:$E${LAST},C{r}),\"fila sem controle\")", "0.0", box=True)
        put(ws, f"F{r}", "=Calculadora!$C$8", "0%", box=True)
    ws["D4"].value, ws["F4"].value = "Dentro da meta", "Meta"
    ch_data = Reference(ws, min_col=4, min_row=4, max_row=15)
    chart = LineChart()
    chart.title, chart.width, chart.height, chart.roundedCorners = "Nível de serviço por tamanho de equipe", 22, 8.5, False
    chart.add_data(ch_data, titles_from_data=True)
    chart.add_data(Reference(ws, min_col=6, min_row=4, max_row=15), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=3, min_row=5, max_row=15))
    chart.title.overlay = False
    chart.legend.position, chart.legend.overlay = "b", False
    chart.x_axis.delete = chart.y_axis.delete = False
    chart.y_axis.scaling.min, chart.y_axis.scaling.max, chart.y_axis.number_format = 0, 1, "0%"
    for serie in chart.series:
        serie.smooth = False
    ws.add_chart(chart, "B18")


def day_schedule(ws, calls_by_hour: list[float]):
    sheet(ws, "Escala de um dia útil", [3, 20, 22, 22])
    put(ws, "B3", "Chamadas previstas: média dos dias úteis do ano de teste (valores do projeto). Premissas: aba Calculadora.", size=9, color="52514E")
    header(ws, 4, 2, ["Chamadas previstas por hora", "Pessoas presentes", "Pessoas a escalar"])
    put(ws, "A4", "Hora", bold=True)
    ws.column_dimensions["A"].width = 7
    for h, calls in enumerate(calls_by_hour):
        r, m = 5 + h, col(9 + 2 * h)
        put(ws, f"A{r}", f"{h}h", box=True)
        put(ws, f"B{r}", round(calls, 1), "#,##0.0", color="0000FF", fill=INPUT, box=True).protection = Protection(locked=False)
        put(ws, f"C{r}", f"=IF(N(B{r})<=0,0,IFERROR(INDEX('Cálculos'!$A${FIRST}:$A${LAST},MATCH(1,'Cálculos'!{m}${FIRST}:{m}${LAST},0)),\"acima de {MAX_N}\"))", "#,##0", box=True)
        put(ws, f"D{r}", f'=IF(ISNUMBER(C{r}),IFERROR(ROUNDUP(ROUND(C{r}/(1-Calculadora!$C$9),9),0),"-"),"-")', "#,##0", box=True)
    put(ws, "A29", "Total", bold=True)
    put(ws, "C29", "=SUM(C5:C28)", "#,##0", bold=True, box=True)
    put(ws, "D29", "=SUM(D5:D28)", "#,##0", bold=True, box=True)
    put(ws, "B30", "Totais em pessoas-hora.", size=9, color="52514E")
    chart = LineChart()
    chart.title, chart.width, chart.height, chart.roundedCorners = "Pessoas por hora", 20, 8.5, False
    chart.add_data(Reference(ws, min_col=3, max_col=4, min_row=4, max_row=28), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=5, max_row=28))
    chart.title.overlay = False
    chart.legend.position, chart.legend.overlay = "b", False
    chart.x_axis.delete = chart.y_axis.delete = False
    for serie in chart.series:
        serie.smooth = False
    ws.add_chart(chart, "F4")


def arrivals(ws, heat: list[list[float]]):
    sheet(ws, "Quando as chamadas chegam", [3, 12] + [5.5] * 24)
    put(ws, "B3", "Média de chamadas de telefone ao NYC 311 por dia da semana e hora (2024-2025, horário de Nova York).", size=9, color="52514E")
    header(ws, 4, 2, ["Dia"] + [f"{h}h" for h in range(24)])
    for i, day in enumerate(["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]):
        r = 5 + i
        put(ws, f"B{r}", day, box=True)
        for h in range(24):
            put(ws, f"{col(3 + h)}{r}", heat[i][h], "0", size=9, box=True)
    ws.conditional_formatting.add("C5:Z11", ColorScaleRule(start_type="min", start_color="F3F8FE", end_type="max", end_color="3987E5"))


def forecast(ws, week: dict):
    pct = lambda v: f"{v * 100:.1f}".replace(".", ",") + "%"  # noqa: E731
    year = week["erros"]
    sheet(ws, "Previsto contra realizado: uma semana", [3, 16, 11, 11, 13, 13, 13, 16, 20])
    put(ws, "B3", f"O erro calculado aqui (WAPE, menor é melhor) vale só para esta semana. No ano inteiro de teste: modelo {pct(year['modelo'])} e regra {pct(year['regra'])}, um empate.", size=9, color="52514E", bold=True)
    header(ws, 4, 2, ["Hora", "Real", "Modelo", "Regra simples", "Erro do modelo", "Erro da regra"])
    stamps = pd.date_range(week["inicio"], periods=168, freq="h")
    for i, ts in enumerate(stamps):
        r = 5 + i
        put(ws, f"B{r}", ts.strftime("%d/%m %Hh"), box=True)
        put(ws, f"C{r}", week["real"][i], "#,##0", box=True)
        put(ws, f"D{r}", week["modelo"][i], "#,##0", box=True)
        put(ws, f"E{r}", week["regra"][i], "#,##0", box=True)
        put(ws, f"F{r}", f"=ABS(C{r}-D{r})", "#,##0", box=True)
        put(ws, f"G{r}", f"=ABS(C{r}-E{r})", "#,##0", box=True)
    put(ws, "I4", "(WAPE)", color="52514E", size=9)
    put(ws, "I5", "Modelo")
    put(ws, "H5", "=IFERROR(SUM(F5:F172)/SUM(C5:C172),0)", "0.0%", bold=True, box=True)
    put(ws, "I6", "Regra simples")
    put(ws, "H6", "=IFERROR(SUM(G5:G172)/SUM(C5:C172),0)", "0.0%", bold=True, box=True)
    ws["H4"] = "Erro na semana"
    ws["H4"].font, ws["H4"].fill = F(bold=True, color="FFFFFF"), HEAD
    ws.freeze_panes = "C5"
    line_chart("Chamadas por hora", "chamadas", Reference(ws, min_col=3, max_col=5, min_row=4, max_row=172),
               Reference(ws, min_col=2, min_row=5, max_row=172), "I9", ws, width=24, height=9)


def build() -> Workbook:
    d = build_data()
    plan = pd.read_parquet(ROOT / "results" / "previsto_realizado.parquet")
    local = plan["hour"].dt.tz_convert(TZ)
    weekdays = plan[local.dt.day_of_week < 5]
    calls = weekdays.groupby(local[weekdays.index].dt.hour)["forecast"].mean()

    wb = Workbook()
    wb.active.title = "Comece aqui"
    names = ["Calculadora", "Contratar ou demitir", "Escala do dia", "Chegadas", "Previsão", "Cálculos"]
    s = {n: wb.create_sheet(n) for n in names}
    start(wb["Comece aqui"])
    from app import logic

    minutes = logic.load_defaults(ROOT)["mean_service"] / 60
    calculator(s["Calculadora"], d["varredura"]["chamadas_hora"], minutes)
    calculations(s["Cálculos"])
    hire_fire(s["Contratar ou demitir"])
    day_schedule(s["Escala do dia"], [float(calls[h]) for h in range(24)])
    arrivals(s["Chegadas"], d["chegadas"]["media"])
    forecast(s["Previsão"], d["previsao"])
    for ws in wb.worksheets:
        ws.protection.sheet = True  # sem senha: só evita apagar fórmulas sem querer
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    return wb


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    build().save(OUT)
    print("OK", OUT, f"{OUT.stat().st_size / 1024:.0f} KB")
