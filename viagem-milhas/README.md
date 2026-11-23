# Verificador de voos (passagens e milhas)

*Leia em: [English](README.en.md)*

Acompanha **todo dia** o preço de uma viagem que **você escolhe** (destinos, datas, passageiros, bagagem e escala mínima), guarda o histórico, **avisa quando o preço cai** e quando aparece **promoção de milhas** com milheiro barato. Também compara dinheiro × milhas e junta, num relatório só, leituras de outros sites (Kayak, CVC, a companhia aérea, programas de milhas).

Funciona para ida e volta, inclusive com **volta de outra cidade** ("open-jaw", ex.: chega por Budapeste e volta por Berlim). Um caso real está em [docs/caso-de-uso-exemplo.md](docs/caso-de-uso-exemplo.md).

## Começando (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -File scripts\setup.ps1          # assistente: pergunta a viagem e cria o config.toml
```

1. **Crie uma conta gratuita na [SerpApi](https://serpapi.com)** (250 consultas/mês) e guarde a chave **só** na variável de ambiente do usuário (nunca em arquivo do projeto):
   `setx SERPAPI_KEY "SUA_CHAVE"` e reabra o terminal.
2. Rode uma vez: `powershell -File scripts\run_daily.ps1`
3. Agende a rotina diária (08:00): `powershell -File scripts\register_task.ps1`

## O que você escolhe

O assistente (`scripts\setup.ps1`) pergunta, e tudo fica no `config.toml` (modelo comentado em [config.example.toml](config.example.toml)):

| Pergunta | Chave no `config.toml` |
|---|---|
| Origem, destino e data da ida | `[trip] outbound` |
| De onde a volta sai, onde chega e a data | `[trip] inbound` (pode ser outra cidade) |
| Passageiros adultos e classe | `[trip] adults`, `cabin` |
| Malas de mão (por pessoa) e despachadas por trecho (e o preço de uma mala) | `[baggage] carry_on`, `checked`, `checked_bag_fee_brl` |
| Escala mínima (horas) | `[rules] min_layover_minutes` |
| Escala máxima que aceita (horas; 0 = sem limite) | `[rules] max_layover_minutes` |
| Aeroportos onde não aceita escala (opcional) | `[rules] avoid_airports` |
| Quanto o preço precisa cair, ou valor-alvo, para avisar | `[alerts] drop_pct`, `target_brl` |

Dá para editar o arquivo à mão a qualquer momento (o programa aceita UTF-8 com ou sem BOM, como o Bloco de Notas grava).

## Interface no navegador

Prefere clicar a digitar? Instale o extra e abra a interface:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-app.txt
powershell -File scripts\app.ps1
```

| Aba | O que faz |
|---|---|
| **Minha viagem** | Formulário com todos os campos (destinos, datas, passageiros, bagagem, escala mínima e máxima, avisos), com validação. Já abre preenchido com a sua configuração atual |
| **Consultar agora** | Faz a consulta na hora, mostra o melhor preço, a diferença para a consulta anterior e todas as ofertas, e **salva a consulta** |
| **Consultas salvas** | Reabre qualquer consulta anterior (a da rotina diária ou as feitas à mão) e compara com a anterior |
| **Histórico** | Gráfico do menor preço por dia, relatório (com a mala estimada) e os últimos avisos |

A interface só mexe em arquivos locais (`config.toml` e `data/`); a rotina diária continua funcionando sem ela.

## Como funciona (parte automática)

Todo dia o Agendador do Windows roda `scripts/run_daily.ps1`, que chama `verificador.run_daily`:

1. **Coleta** (`collector.py`): consulta a SerpApi (Google Voos). A 1ª chamada devolve as **idas**; para cada uma das 3 idas mais baratas que passam nas regras, uma chamada com `departure_token` devolve as **voltas** e o **preço total** do grupo. No máximo **4 consultas/dia**. A mala de mão só vai na busca se você ligar `send_to_api` (desligado por padrão: o filtro do Google esconde ofertas válidas).
2. **Filtro** (`rules.py`): descarta ofertas com escala abaixo do mínimo (ou sem duração informada) ou em aeroportos que você evita, e fica com a mais barata.
3. **Histórico** (`history.py`): uma linha por dia em `data/history.csv`. Rodar duas vezes no mesmo dia não duplica, e uma falha nunca apaga o preço bom do dia. Além disso, **cada consulta é salva inteira** em `data/snapshots/` (todas as ofertas, com as escalas e se passam nas regras), para você rever e comparar no dia seguinte.
4. **Avisos** (`alerts.py`): notificação do Windows + `data/alerts.log` quando o preço cai o suficiente, **cruza para baixo do valor-alvo** (só na travessia, não todo dia), ou a coleta falha ou volta vazia.
5. **Promoções** (`promos.py`): lê os feeds de blogs de milhas e avisa só quando o **milheiro** citado fica abaixo do limite (Flying Blue, TAP, Livelo e Smiles, ajustável). Cada post é avisado uma vez.

## Leituras sob demanda (parte manual)

Kayak, CVC e programas de milhas têm proteção contra robô ou exigem login, então não rodam sozinhos. Quando você (ou um assistente) lê um preço lá, grave:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m verificador.other_sources --source kayak --price 19152 --note "Light"
.venv\Scripts\python.exe -m verificador.other_sources --source "flying blue" --miles 502000 --taxes 3000
.venv\Scripts\python.exe -m verificador.report
```

O relatório mostra o Google Voos (série automática), a leitura mais recente de cada fonte, o menor preço em dinheiro, o **total com a bagagem despachada estimada** e o **milheiro de equilíbrio** (preço abaixo do qual as milhas ganham do dinheiro).

## Comandos

| O que | Comando |
|---|---|
| Configurar a viagem | `powershell -File scripts\setup.ps1` |
| Abrir a interface no navegador | `powershell -File scripts\app.ps1` |
| Rodar agora | `powershell -File scripts\run_daily.ps1` |
| Registrar a tarefa diária (08:00) | `powershell -File scripts\register_task.ps1` |
| Remover a tarefa | `Unregister-ScheduledTask -TaskName VerificadorPassagens -Confirm:$false` |
| Relatório combinado | `.venv\Scripts\python.exe -m verificador.report` (com `PYTHONPATH=src`) |
| Calculadora dinheiro × milhas | `.venv\Scripts\python.exe -m verificador.calculator --cash 19152 --miles 502000 --milheiro 30 --taxes 3000` |
| Testes | `.venv\Scripts\python.exe -m pytest -q` |

Arquivos de dados (ignorados pelo git): `config.toml`, `data/history.csv`, `data/snapshots/`, `data/outras_fontes.csv`, `data/seen_promos.json`, `data/alerts.log`.

## Limites e cuidados

- O preço do Google Voos difere do de outros sites (opções e tarifas listadas diferentes). Os avisos valem para a série do Google Voos.
- Tarifas "Light" não incluem mala despachada; o relatório soma uma **estimativa** (você informa o preço da mala).
- Milhas não são consultadas automaticamente (cada programa exige login); entram pela calculadora, pelas leituras manuais e pelo vigia de promoções.
- Se os feeds de blogs ficarem fora do ar, só as promoções ficam sem vigia (o preço da passagem continua).
- A SerpApi muda limites e preços; confira no site dela. A chave nunca deve ir para o repositório.

Documentos: desenho `docs/2026-11-23-verificador-passagens-design.md` · plano `docs/superpowers/plans/` · notas da SerpApi `docs/spike-serpapi.md` (escritos para o caso de uso original).
