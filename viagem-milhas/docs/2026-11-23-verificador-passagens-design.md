# Verificador de passagens e milhas — desenho

Data: 23/11/2026. Status: aprovado e implementado (veja o README).

## Intenção e por quê

Dois viajantes querem viajar à Europa em julho de 2027 e baixar o máximo possível o custo da passagem. A pesquisa feita em 23/11/2026 mostrou que, hoje, **pagar em dinheiro é o melhor caminho**; milhas só vencem se aparecer uma promoção fora do comum. O verificador existe para (1) acompanhar o preço em dinheiro ao longo dos meses, (2) avisar quando ele cair e (3) avisar quando surgir uma promoção de milhas que mude a conta. A ideia é decidir a hora de comprar com dados, não no susto.

## Fatos fixos

- Trajeto, datas fixas: ida **GIG → BUD (Budapeste) em sáb 10/07/2027**; volta **BER (Berlim) → GIG em qui 22/07/2027**. É "open-jaw": a volta NÃO sai de Budapeste.
- 2 adultos, econômica.
- Regras do Sérgio: toda escala com **no mínimo 4h** (imigração); **nenhuma escala no Brasil** (voos saem e chegam no Galeão).
- Referência de hoje: KLM, ida 21:55 (escala de 7h em Amsterdã), volta 06:00 (escala de 5h25 em Amsterdã), tarifa Light (sem mala despachada): **R$ 19.152 no total**.
- Referência em milhas (Flying Blue, mesmo voo): ida 230.000 + volta 272.000 = **502.000 milhas + taxas**. Ponto de equilíbrio contra o dinheiro: milheiro abaixo de uns **R$ 30–32** (supondo ~R$ 3 mil de taxas, ainda não confirmado).
- Hoje o milheiro mais barato que se achou via Livelo para o Flying Blue é ~R$ 68–100, bem acima do equilíbrio.

## Metas

1. Registrar todo dia o **menor preço total** (ida + volta) que passe nas regras, com a companhia e as escalas.
2. Guardar o histórico e mostrar a evolução (tabela e gráfico simples).
3. **Avisar** quando o preço cair mais que um limite (ver Decisões) ou ficar abaixo de um valor-alvo.
4. **Vigiar o feed de notícias dos blogs de milhas** (Passageiro de Primeira, Pontos pra Voar) atrás de promoções de Flying Blue, Smiles, Livelo e TAP com milheiro baixo, e avisar.
5. Uma **calculadora** que compara "dinheiro" contra "milhas + compra" a partir de: milhas necessárias, preço do milheiro, taxas e o preço em dinheiro do dia.

## Não-metas

- Não compra passagem, não faz reserva, não transfere pontos.
- Não consulta preço em milhas automaticamente (exige login em cada programa). Milhas entram na calculadora por digitação, e as promoções vêm do feed.
- Não resolve CAPTCHA nem burla bloqueio de robô.

## Anti-metas (seria fracasso mesmo funcionando)

- Chover aviso à toa (alerta toda hora, por oscilação pequena).
- Quebrar em silêncio: se a coleta falhar ou o limite da API acabar, o Sérgio precisa ser avisado.
- Vazar a chave da API ou dados pessoais (chave só em variável de ambiente, nunca no código nem no repositório).

## Restrições

- Windows 11, Python, rodando no computador do Sérgio; agenda pelo Agendador de Tarefas do Windows.
- Custo zero ou muito baixo: plano gratuito da API (SerpApi: 250 consultas/mês; uma por dia usa ~30).
- Poucos tokens: depois de pronto, roda sem o Claude.
- Dados ficam locais (arquivos CSV/SQLite na pasta do projeto).

## Abordagens consideradas

| | O que é | Prós | Contras |
|---|---|---|---|
| A | Claude roda em agenda, abre o Kayak e anota | Sem código de coleta; reaproveita o que funcionou | Gasta tokens a cada rodada; depende do app aberto |
| **B (escolhida)** | Script Python + API de preços; Agendador do Windows roda diário | Confiável, sem tokens depois de pronto, bom pro portfólio | Precisa criar conta na API; confirmar limites |
| C | Planilha manual | Nunca quebra | Não avisa sozinha |

Escolha do Sérgio: **B**, em 23/11/2026.

**Qual API dentro do B.** A API self-service da Amadeus foi desligada em julho de 2026 e saiu das opções. Escolhida: **SerpApi (Google Voos)** pelo plano gratuito. Plano reserva: Duffel. Ainda **não confirmado**: se a SerpApi aceita busca de múltiplos trechos (open-jaw). Se não aceitar, a alternativa é duas buscas só de ida por dia (GIG→BUD e BER→GIG) somando os preços, o que dobra o consumo (~60/mês, ainda dentro do gratuito) e, pela pesquisa de hoje, tende a dar preço MAIOR que o combinado — por isso o primeiro passo do plano deve validar isso.

## Desenho

Peças, cada uma em seu arquivo:

1. **Coletor**: chama a API para o trajeto open-jaw, 2 adultos, econômica, moeda BRL; guarda a resposta bruta do dia.
2. **Filtro de regras**: de todas as ofertas, descarta as que têm escala < 4h ou escala no Brasil; escolhe a mais barata que passa.
3. **Histórico**: uma linha por dia (data, preço total, companhias, escalas, tarifa, se a resposta foi completa).
4. **Alertas**: compara com o histórico; envia aviso se (a) caiu mais que o limite desde a última referência, (b) ficou abaixo do valor-alvo, ou (c) houve falha na coleta.
5. **Vigia de promoções**: lê os feeds RSS dos blogs; procura palavras-chave (Flying Blue, Smiles, Livelo, TAP, "bônus", "milheiro", "R$ ..."), extrai o preço do milheiro quando houver, e avisa só quando for menor que o limite.
6. **Calculadora**: função/planilha que recebe milhas, milheiro e taxas e devolve o custo total e se vence o dinheiro.
7. **Configuração**: um arquivo com trajeto, datas, regras e limites; a chave da API em variável de ambiente.

Fluxo diário: Agendador → coletor → filtro → histórico → alertas; o vigia de promoções roda junto, uma vez por dia.

## Decisões do Sérgio (como ele decidiu)

- Abordagem B; trajeto, datas e regras como acima.

## Decisões minhas (para o Sérgio conferir)

- **Frequência**: 1 coleta por dia, de manhã.
- **Aviso**: notificação do Windows + registro em arquivo; e-mail pode vir depois.
- **Limite de queda**: avisar se o preço cair **5% ou mais** desde a última referência; **valor-alvo** inicial R$ 18.000 (ajustável).
- **Limite de milheiro** nos blogs: avisar se o milheiro citado for **menor que R$ 35** para Flying Blue/TAP ou **menor que R$ 12** para Smiles (ajustável).
- **Armazenamento**: CSV simples (sem banco), fácil de abrir no Excel.
- **Pasta**: `viagem-milhas/` dentro de `portfolio - github`.

## O que fica para quem for construir

Nomes de arquivos e funções, biblioteca de leitura de RSS, formato exato do aviso do Windows, como lidar com resposta parcial da API e testes. Primeiro passo obrigatório: validar com uma chamada real se a SerpApi devolve o trajeto open-jaw com os dados de escala necessários para o filtro.

## Riscos conhecidos

- O Google Voos pode não listar as mesmas tarifas/companhias que o Kayak (ex.: KLM Light de R$ 19.152).
- O filtro de 4h depende de a API informar a duração de cada escala.
- Limites e preços da API mudam; conferir no site oficial antes de assinar.
- O preço não inclui mala despachada em tarifas Light/Basic.

## Atualizações depois da aprovação (23/11/2026)

- **Regra do Brasil removida.** "Nenhuma escala no Brasil" foi suposição nossa; o Sérgio nunca pediu. Fica só a regra das 4h. Fica em `config.toml` (`brazil_airports = []`) caso queiram reativar.
- **Coletor com chamadas encadeadas.** A SerpApi devolve primeiro as idas e só depois, por `departure_token`, as voltas (ver `spike-serpapi.md`). Até 4 consultas por dia.
- **Aviso de valor-alvo só na travessia** (e não todo dia enquanto o preço estiver baixo), e **falha no mesmo dia não apaga o preço bom** já gravado.
- **Leituras sob demanda adicionadas** (não faziam parte do desenho): `outras_fontes.csv` + `report`, para juntar Kayak, CVC, KLM e programas de milhas ao Google Voos.
- **Preferências novas do Sérgio:** 2 malas de mão + 1 despachada para os dois; parada longa só se custar menos de R$ 1 mil a mais.
