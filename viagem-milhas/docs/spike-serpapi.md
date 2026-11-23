# Spike SerpApi (Google Voos) — 23/11/2026

Duas chamadas reais gastaram 2 das 250 consultas gratuitas do mês.

## Resultado

- **Funciona com o trajeto aberto.** `engine=google_flights`, `type=3` (multi-city) com `multi_city_json` = `[GIG→BUD 2027-07-10, BER→GIG 2027-07-22]`, `adults=2`, `currency=BRL`, `hl=pt`, `gl=br`, `travel_class=1`.
- **(a) Preço total vem em etapas.** A 1ª chamada devolve só as opções de **ida** (`best_flights` + `other_flights`), cada uma com `departure_token`. Chamando de novo com `departure_token=<token>` (mesmos parâmetros) vem a lista de **voltas** (`other_flights`), e o `price` de cada volta é o **total da viagem para os 2 adultos** (ida escolhida + volta).
- **(b) Duração de escala disponível**: `layovers[]` com `id` (IATA) e `duration` (minutos), por oferta.
- **(c) Custo em consultas**: 1 chamada para as idas + 1 por ida expandida. Decisão: expandir no máximo as **3 idas mais baratas que passam nas regras** → até 4 consultas/dia ≈ 120/mês (dentro do plano gratuito de 250).

## Observações

- Em 23/11/2026 a 1ª chamada trouxe 9 idas; 5 passam nas regras (4h, sem Brasil). Uma volta KLM listada tinha escala de 140 min (reprovada). A volta KLM das 06:00 com 5h25 em Amsterdã, vista no Kayak, **não apareceu** nessa resposta: o Google Voos mostra menos opções que o Kayak.
- Preço do Google Voos para a ida KLM 21:55 + volta KLM: R$ 19.400 (Kayak: R$ 19.152 com outra volta). Pequena diferença é esperada.
- A resposta não traz a marca da tarifa (Light etc.): `fare` fica `None`.
- A chave nunca aparece na resposta crua; mesmo assim as fixtures foram gravadas com a chave substituída por `***`.

Fixtures: `tests/fixtures/serpapi_open_jaw.json` (idas) e `tests/fixtures/serpapi_open_jaw_leg2.json` (voltas após a ida KLM).
