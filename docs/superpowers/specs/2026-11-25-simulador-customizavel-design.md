# Simulador de filas customizável com analisador de entrada: design

Data: 2026-11-25
Status: rascunho aguardando aprovação do Sérgio (nada implementado).
Estende: `2026-11-24-dimensionamento-equipe-design.md` (projeto `portfolio-ds/dimensionamento-equipe/`).

## Intenção e por quê

Hoje a simulação do projeto tem só duas formas de atendimento (exponencial e lognormal com CV escolhido por mim) e os parâmetros de atendimento (360 s) são premissa fictícia. O Sérgio vem do Arena: lá se escolhe a distribuição de cada entrada e o Input Analyzer diz qual se ajusta melhor aos dados. O objetivo é levar essa lógica para o projeto: o usuário monta o cenário com a distribuição que quiser, e o projeto traz a sua própria proposta **ajustada em dado real**, mostrando o ranking aberto, para o usuário poder testar algo melhor.

Também resolve o ponto fraco do README atual: o tempo de atendimento deixa de ser só premissa, porque passa a vir de uma base com tempos reais de atendimento.

## Objetivos

1. **Analisador de entrada** (estilo Input Analyzer): dado um conjunto de valores, ajusta distribuições candidatas, ranqueia e mostra histograma com as curvas ajustadas.
2. **Simulador generalizado**: chegadas e atendimento aceitam qualquer distribuição escolhida (nome e parâmetros), não só as duas de hoje.
3. **Cenário do usuário** descrito em arquivo YAML (distribuições, parâmetros, número de agentes, meta de serviço) e rodável por linha de comando e notebook.
4. **App web local (Streamlit)** onde o usuário escolhe distribuições num menu, vê o ajuste e o ranking, roda a simulação e compara com o Erlang C.
5. **Base real de atendimento: Technion "Anonymous Bank"** (call center de banco em Israel, 1999, tempos reais de atendimento, espera e abandono). O ajuste sobre ela gera a distribuição **proposta**.
6. **Independência**: o projeto e o app funcionam sem o usuário carregar nada. Carregar o próprio arquivo é opcional.
7. **Validação contra o dado real**: simular o call center do próprio banco e comparar a espera simulada com a espera que ele teve, reportando a diferença como saiu.

## Não objetivos

- Reproduzir o Arena (blocos, animação, modelagem por fluxograma).
- Abandono de fila na simulação (os clientes do banco desistem; o Erlang C e o simulador ignoram isso). O README diz; modelar abandono (Erlang A) fica como extensão futura.
- Múltiplas filas, prioridades e roteamento por habilidade.
- Hospedar o app na internet (roda local).
- Mexer em Datadog, Salesforce, contas ou credenciais.

## Anti-objetivos (seria fracasso mesmo funcionando)

- O app ou o README só funcionarem se alguém baixar ou carregar um arquivo.
- Afirmar que a distribuição proposta "é a melhor" sem mostrar o ranking completo e os critérios; ou escrever essa afirmação antes de o código rodar.
- Esconder que os testes de aderência rejeitam tudo com amostras grandes (centenas de milhares de pontos) e ranquear só por p-valor.
- Misturar as bases (chegadas do NYC 311, atendimento do Technion) sem dizer isso com todas as letras no README e no app.
- Mensagem de e-mail ao professor Mandelbaum enviada em nome do Sérgio sem ele mandar.

## Restrições

- Sem commit nem push até o Sérgio pedir; sem criar contas.
- Specs primeiro, testes antes do código.
- Todo número do README, do notebook e do app sai de código rodado (`results/results.json` ou saída do próprio motor).
- Fonte dos dados reais: citar o Technion SEE Center (Anonymous Bank, documentação de Guedj e Mandelbaum, 2000) no README e no app. A condição de uso (avisar o professor Avi Mandelbaum) fica registrada no README como pendência do Sérgio, que decide se e quando avisar.
- Instalar dependências novas (Streamlit) e baixar `AnonymousBank.rar` (10,6 MB, `see-center.iem.technion.ac.il`) só com o sim do Sérgio no momento.
- README em português e inglês.

## Abordagens consideradas

- A. Arquivo YAML mais linha de comando e notebook. Simples e testável, pouca sensação de Arena. Vira a base de B.
- **B. A mais app web local em Streamlit (escolhida pelo Sérgio).** Menu de distribuições, upload opcional, ranking e gráficos, simulação na hora. A lógica fica na biblioteca; o app é uma camada fina. Custo: mais trabalho e uma dependência nova.
- C. Só notebook com widgets. Exige Python do usuário; descartada.

## Decisões do Sérgio

- Usar a base do Technion, explicando o que é e por que foi usada.
- Permitir que o usuário informe a base de atendimento que quiser testar.
- Abordagem B.
- O projeto funciona sozinho: nada depende de o usuário carregar arquivo.

## Escolhas minhas (propostas)

- **Independência na prática:** o repositório leva amostras derivadas pequenas e prontas: (a) tempos de atendimento reais do Technion (só `ser_time` dos atendidos, mais tipo de serviço e hora do dia), (b) a série horária do NYC 311 já agregada. Teto de tamanho: cerca de 5 MB no total. Junto, um arquivo `FONTES.md` com origem, termos e agradecimento. O download do arquivo bruto do Technion é só para quem quiser reproduzir o preparo; o app nunca baixa nada sozinho.
- **Cenário padrão do app:** chegadas vindas do NYC 311 (previsão por hora, como hoje) e atendimento = distribuição de melhor ajuste nos tempos do Technion, com o ranking visível. O app abre já com esse cenário rodado.
- **Candidatas do analisador:** exponencial, gama, Weibull, lognormal, Erlang, normal, beta, triangular, uniforme. **Critério de ordenação: AIC**, mostrando também BIC, estatística KS e erro quadrático (como o Arena). O p-valor aparece só como informação, com aviso de que perde sentido em amostras grandes e com parâmetros estimados.
- **Chegadas:** a simulação mantém chegadas por hora a partir da previsão (taxa constante dentro da hora), mas o usuário pode escolher a distribuição dos intervalos entre chegadas. O analisador de chegadas roda sobre os intervalos reais do NYC 311 por faixa de hora, para testar a hipótese de Poisson do Erlang C.
- **Validação com o banco:** repetir as chegadas reais de uma faixa de horas do Technion (replay), usar o atendimento ajustado e o número de agentes da documentação, e comparar espera média e nível de serviço simulados com os reais. A diferença é reportada, com a ressalva do abandono; não se promete que bata.
- **Arquivo do usuário:** CSV de uma coluna (ou coluna escolhida), valores positivos em segundos. Linhas inválidas (vazias, negativas, não numéricas, zero) são descartadas e contadas, e o app mostra quantas.
- **App:** `app/app.py`, rodado com `streamlit run`. Gráficos em matplotlib (sem dependência extra).

## Estrutura proposta (acréscimos)

```
dimensionamento-equipe/
  src/input_analyzer.py      # ajuste, ranking, amostrador
  src/scenario.py            # carrega/valida cenário YAML, monta amostradores
  src/simulation.py          # generalizado (aceita amostradores)
  scripts/preparar_technion.py   # extrai tempos do .rar bruto (opcional)
  app/app.py                 # camada Streamlit
  data/exemplos/             # amostras derivadas committadas + FONTES.md
  config/cenario_exemplo.yaml
  tests/ test_input_analyzer.py test_scenario.py test_simulation.py (ampliado) test_app.py
```

## Verificação

- **Analisador:** amostras sintéticas de distribuições conhecidas (lognormal, gama, exponencial, Weibull): a de origem aparece entre as 2 melhores por AIC; histograma e ranking não quebram com amostras pequenas; amostra com menos pontos que o mínimo declarado dá erro claro.
- **Entradas inválidas:** NaN, negativos, zeros, coluna inexistente, arquivo vazio, valores gigantes: tratados e contados, sem exceção.
- **Simulador:** com atendimento exponencial e chegadas de Poisson reproduz o Erlang C dentro da tolerância já existente (testes atuais continuam passando); com qualquer outra distribuição, a média e o CV amostrados batem com os parâmetros pedidos.
- **Cenário YAML:** validação de nomes de distribuição, parâmetros fora do domínio e agentes menores que 1.
- **App:** teste sem navegador (`streamlit.testing.v1.AppTest`) provando que abre e roda **sem nenhum upload**, e que com upload válido e inválido não quebra.
- **Validação com o Technion:** número de ligações e período conferidos contra a documentação; resultado da comparação guardado em `results.json` e citado no README só a partir dele.
- **Independência:** teste que remove `data/raw` e `results/` temporariamente e confirma que o app abre com os exemplos incluídos.

## Riscos e pré-requisitos

- **Formato do `.rar`:** precisa de extrator; o Windows recente costuma abrir com `tar`, mas será confirmado antes de baixar. Se não abrir, o plano para e pergunta.
- **Campos exatos** dos arquivos mensais vêm da documentação (17 campos, tempos em hh:mm:ss e segundos); confirmar nos arquivos antes de congelar o preparo.
- **Dados de 1999 e de um banco em Israel:** o cenário padrão mistura essa fonte com o NYC 311. O app e o README dizem isso, e dizem que o atendimento é o único elo real com a base do banco.
- **Avisar o professor Mandelbaum** é decisão do Sérgio (o README só registra).
- Streamlit ainda não está no ambiente `C:\venvs\wfm`; instalar depende do sim do Sérgio.

## Depois de pronto

Atualizar a entrada `dimensionamento-equipe` em `Dropbox\Carreira\base\projetos.yaml` com o que foi verificado e **perguntar ao Sérgio** antes de pôr em qualquer versão do currículo (versão Dados no limite de 2 páginas). As mudanças vão para a branch do PR nº 8 ou para um PR novo, conforme o Sérgio preferir.

## O que fica para quem constrói

Nomes de funções, layout do app, estilo dos gráficos, texto dos avisos, tamanho mínimo de amostra do analisador, e a lista exata dos candidatos que entram no menu inicial.
