# Verificador de passagens e milhas

*Leia em: [English](README.en.md)*

Acompanha o preço da viagem **ida GIG → Budapeste (sáb 10/07/2027), volta Berlim → GIG (qui 22/07/2027)**, 2 adultos, econômica. A volta **não** sai de Budapeste: é "open-jaw".

O verificador roda sozinho todo dia, guarda o histórico, avisa quando o preço cai e quando surge promoção de milhas barata. As leituras em outros sites (Kayak, CVC, KLM, programas de milhas) são feitas sob demanda e gravadas ao lado, para comparar tudo num relatório só.

Documentos: desenho `docs/2026-11-23-verificador-passagens-design.md` · plano `docs/superpowers/plans/2026-11-23-verificador-passagens.md` · notas da SerpApi `docs/spike-serpapi.md`.

## Regras da busca

- **Escala de 4h no mínimo** em toda conexão, ida e volta (por causa da imigração). É a única regra de escala do Sérgio.
- A regra "nenhuma escala no Brasil" **foi removida** (era suposição nossa, nunca foi pedida). Para reativar, liste aeroportos em `brazil_airports` no `config.toml`.
- Bagagem: **2 de mão + 1 despachada** para os dois. Tarifas "Light" não incluem despachada; some o preço da mala ao comparar.
- Uma parada longa (~24h) numa cidade só vale se custar **menos de R$ 1 mil** a mais que a melhor opção sem parada.

## Como funciona (parte automática)

Todo dia às 08:00 o Agendador do Windows roda `scripts/run_daily.ps1`, que chama `verificador.run_daily`:

1. **Coleta** (`collector.py`): consulta a SerpApi (Google Voos) com o trajeto aberto. A 1ª chamada devolve as **idas**; para cada uma das 3 idas mais baratas que passam nas regras, uma chamada com `departure_token` devolve as **voltas** e o preço **total para os 2**. No máximo **4 consultas/dia** (~120 de 250/mês no plano gratuito).
2. **Filtro** (`rules.py`): descarta ofertas com escala abaixo de 4h (ou sem duração informada) e fica com a mais barata.
3. **Histórico** (`history.py`): grava uma linha por dia em `data/history.csv`. Rodar duas vezes no mesmo dia não duplica, e uma falha não apaga o preço bom do dia.
4. **Avisos** (`alerts.py`): notificação do Windows + `data/alerts.log` quando: o preço cai **5% ou mais** desde o dia anterior; **cruza para baixo de R$ 18.000** (só na travessia, não todo dia); a coleta falha ou volta vazia.
5. **Promoções** (`promos.py`): lê os feeds do Passageiro de Primeira e do Pontos pra Voar; avisa só quando o **milheiro** citado fica abaixo do limite (Flying Blue, TAP e Livelo < R$ 35; Smiles < R$ 12). Cada post é avisado uma vez.

Limites, preços-alvo, trajeto e feeds ficam em `config.toml`. A chave da SerpApi fica **só** na variável de ambiente do usuário `SERPAPI_KEY` (nunca em arquivo do projeto).

## Leituras sob demanda (parte manual)

Sites como Kayak, CVC e os programas de milhas têm proteção contra robô ou exigem login, então não rodam sozinhos. Quando o Sérgio pede "atualiza", o Claude abre o site, lê o preço e grava:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m verificador.other_sources --source kayak --price 19152 --note "KLM Light"
.venv\Scripts\python.exe -m verificador.other_sources --source "flying blue" --miles 502000 --taxes 3000
.venv\Scripts\python.exe -m verificador.report
```

O relatório mostra o Google Voos (série automática) e a leitura mais recente de cada fonte, o menor preço em dinheiro e o **equilíbrio do milheiro** (preço do milheiro abaixo do qual as milhas ganham do dinheiro).

Endereços úteis (já com o trajeto):
- Kayak: `https://www.kayak.com.br/flights/GIG-BUD/2027-07-10/BER-GIG/2027-07-22/2adults?sort=price_a`
- CVC: `https://www.cvc.com.br/passagens/v3/busca/GIG/BUD/BER/GIG?dates=2027-07-10&dates=2027-07-22&adults=2&cabin=economy`
- KLM: klm.com.br → "Múltiplos destinos" (com "Reservar com Milhas" desligado para ver preços em reais; ligado, a busca é por trecho e exige login Flying Blue).

## Comandos

| O que | Comando |
|---|---|
| Rodar agora | `powershell -File scripts\run_daily.ps1` |
| Registrar a tarefa diária (08:00) | `powershell -File scripts\register_task.ps1` |
| Remover a tarefa | `Unregister-ScheduledTask -TaskName VerificadorPassagens -Confirm:$false` |
| Relatório combinado | `.venv\Scripts\python.exe -m verificador.report` (com `PYTHONPATH=src`) |
| Calculadora dinheiro × milhas | `.venv\Scripts\python.exe -m verificador.calculator --cash 19152 --miles 502000 --milheiro 30 --taxes 3000` |
| Testes | `.venv\Scripts\python.exe -m pytest -q` |

Arquivos de dados (ignorados pelo git): `data/history.csv` (colunas: data, preço total, companhias, escalas, tarifa, status `ok`/`empty`/`error`), `data/outras_fontes.csv`, `data/seen_promos.json`, `data/alerts.log`.

## Estado em 23/11/2026 (referência)

| Fonte | Total para os 2 | Observação |
|---|---|---|
| **KLM Light** (Kayak e site da KLM) | **R$ 19.152** | Ida 21:55 (7h em Amsterdã), volta 06:00 (5h25 em Amsterdã). Sem mala despachada |
| KLM Light + 1 mala por trecho | ~R$ 20.350 a 20.650 | **Estimativa**: mala ~US$ 100–120 por trecho, preço exato só no fim da reserva. Ida Standard (com mala) = +R$ 883; a volta só tem tarifa Light |
| Lufthansa Economy Light | R$ 20.005 | Volta com 13h30–14h30 em Frankfurt, sem mala despachada |
| Google Voos (série automática) | R$ 21.440 | Lista menos opções que o Kayak; compare-o só com o dia anterior dele mesmo |
| CVC (Turkish, mala incluída) | R$ 20.035 | **Reprova**: escala de 3h15 em Istambul na volta |
| Paradas de ~24h (Londres, Lisboa, Madri) | R$ 22.189 a 24.826 | ≥ R$ 3 mil acima: fora pela regra do R$ 1 mil |
| Flying Blue (milhas) | 502.000 milhas + taxas | Equilíbrio ≈ R$ 32/milheiro; mais barato achado via Livelo: ~R$ 68–100 |
| Smiles (milhas) | mais de 3× o Flying Blue | 330.500 a 360.700 milhas por pessoa só na ida |

Conclusão de hoje: **pagar em dinheiro a KLM Light** é o melhor caminho; milhas só ganham com milheiro abaixo de ~R$ 30.

## Limites e cuidados

- O preço do Google Voos difere do Kayak (opções e tarifas listadas diferentes). Os avisos valem para a série do Google Voos.
- Tarifas Light não incluem mala despachada; combine o preço da mala antes de decidir.
- Milhas não são consultadas automaticamente (cada programa exige login); entram pela calculadora, pela leitura sob demanda e pelo vigia de promoções.
- Se os dois feeds de blogs ficarem fora do ar juntos, só as promoções ficam sem vigia (o preço da passagem continua).
- A SerpApi muda limites e preços; confirme no site dela antes de assinar qualquer plano pago.
