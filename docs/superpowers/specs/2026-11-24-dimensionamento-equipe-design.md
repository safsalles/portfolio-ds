# Dimensionamento de equipe a partir da previsão de demanda por hora: design

Data: 2026-11-24
Status: rascunho aguardando aprovação do Sérgio (nada implementado).

## Intenção e por quê

Vagas de analista sênior de Operações e BI pedem PySpark, séries temporais, dimensionamento de equipe (Erlang C), simulação de filas, Git, testes e alertas. O projeto mostra isso com código que roda: parte de uma base pública real de contatos, prevê a demanda por hora, calcula quantas pessoas são necessárias para uma meta de serviço, confere o resultado por simulação e monitora previsto contra realizado com alerta.

Pasta nova: `portfolio-ds/dimensionamento-equipe/`, seguindo o padrão das outras (README.md e README.en.md, requirements.txt, pytest, notebook de análise).

## Objetivos

1. **Pipeline PySpark** (local) que limpa e agrega o dado bruto do NYC 311 em contagens de chamadas por hora.
2. **Previsão por hora** com sazonalidade por hora e dia da semana, comparada com uma regra simples, para mostrar quanto o modelo ganha. Avaliação sempre fora da amostra.
3. **Erlang C**: pessoas necessárias por hora para atender dentro do tempo de espera alvo, com testes automatizados.
4. **Cenários de meta de serviço**: comparar, por exemplo, 80/20 contra 90/30, mostrando quantas pessoas cada meta custa (decidido pelo Sérgio).
5. **Simulação de filas** do mesmo cenário, para conferir se bate com o Erlang C, mais uma variação com atendimento menos "ideal" para mostrar onde o Erlang C erra.
6. **Monitoramento intraday**: previsto contra realizado, com alerta por webhook de teste do Slack.
7. **Notebook de análise** que conta a história com gráficos, importando o pacote.
8. Opcional, só se sobrar fôlego: pergunta em linguagem natural ("quantas pessoas preciso na sexta às 14h?") consultando o modelo.

## Não objetivos

- Integração com Datadog ou Salesforce.
- Rodar em produção, agendar execuções ou manter serviço no ar.
- Treinar nada pesado (rede neural, Prophet). O modelo é simples e explicável.
- Escalonamento de turnos e escala individual (quem trabalha em que horário). O resultado é "pessoas por hora", não uma escala.
- Criar conta por conta própria (Databricks, Slack, Kaggle). O que exigir conta fica preparado e marcado como não executado.

## Anti-objetivos (seria fracasso mesmo funcionando)

- Qualquer número no README que não saia de código rodado.
- Apresentar a equipe, o tempo de atendimento ou a meta de serviço como dado real. São premissas fictícias, ditas como tal.
- Afirmar que o projeto rodou no Databricks sem que o Sérgio tenha rodado lá.
- Modelo que só parece bom porque foi avaliado nos mesmos dados em que treinou.

## Restrições

- Sem commit nem push até o Sérgio pedir.
- Não criar contas. Nada de credenciais reais no repositório; o webhook do Slack é de teste e fica em variável de ambiente, nunca no código.
- Specs primeiro, testes antes do código (TDD), como no gerador de currículos.
- Baixar o dado do portal NYC Open Data é um download: o Sérgio autoriza no momento, com nome do arquivo, fonte e tamanho informados antes.
- README em português e em inglês. Código e dados brutos ficam fora do versionamento quando grandes (`data/` no `.gitignore`).

## Abordagens consideradas

- **A. Pacote Python com módulos, testes e um notebook que só conta a história (escolhida pelo Sérgio).** Cada etapa em `src/`, testável. Ganha em credibilidade e padrão com as outras pastas. Custo: mais trabalho inicial.
- B. Tudo em notebooks. Mais rápido, mas sem pytest de verdade e com Erlang C e simulação difíceis de testar. Descartada.
- C. Databricks desde o início. Amarra o projeto a uma conta que o Sérgio ainda não tem. Descartada; Databricks vira bônus.

## Decisões já tomadas

- **Base de dados:** NYC 311 Service Requests (NYC Open Data), filtrada pelo canal telefone. A Olist foi descartada: sem volume por hora nem relação com atendimento. A decisão veio do Sérgio.
- **Cenários de meta de serviço:** o projeto compara pelo menos 80/20 e 90/30 (Sérgio).
- **PySpark:** completo e verificado local, só com API de DataFrame. **Databricks:** notebook de entrada preparado, marcado no README como "preparado, não executado" até o Sérgio rodar lá.

## Escolhas minhas (propostas, o Sérgio pode trocar)

- **Horário de chegada:** o campo de data de abertura do chamado é tratado como o momento em que o contato chegou. O README diz que é uma aproximação.
- **Recorte:** 2 anos completos e recentes. O primeiro ano treina, o segundo testa. Os anos exatos e o canal telefone são confirmados no dado antes de congelar.
- **Regra simples (referência):** média das últimas 4 semanas na mesma hora e dia da semana.
- **Modelo:** regressão de contagem (Poisson) com hora × dia da semana, feriados e tendência. Erro medido por WAPE e MAPE, comparado com a regra simples, só no ano de teste.
- **Premissas fictícias do Erlang C:** tempo médio de atendimento (proposta: 6 min), folga para ausências e pausas (proposta: 30%), cenários 80/20 e 90/30. Os valores finais ficam num arquivo de configuração e no README como premissa, não como dado.
- **Simulação:** eventos discretos, chegadas de Poisson e atendimento exponencial (casando com a premissa do Erlang C). Variação com atendimento lognormal para mostrar a diferença. Critério de "bate": nível de serviço simulado dentro de uma tolerância declarada do valor do Erlang C, com semente fixa e réplicas.
- **Alerta:** compara previsto e realizado hora a hora (dia de teste reproduzido como se fosse intraday) e dispara mensagem para um webhook de teste do Slack quando o desvio passa de um limite configurável. Nos testes o webhook é simulado; o envio real só roda se o Sérgio fornecer a URL.

## Estrutura proposta

```
dimensionamento-equipe/
  README.md  README.en.md  requirements.txt  .gitignore
  config/premissas.yaml        # tempo de atendimento, metas, folga, limite do alerta
  data/raw  data/processed     # fora do versionamento
  src/
    pipeline.py                # PySpark: limpar, filtrar telefone, agregar por hora
    forecast.py                # regra simples e modelo, métricas
    erlang.py                  # Erlang C, pessoas necessárias, cenários
    simulation.py              # simulação de filas e comparação com Erlang C
    monitor.py                 # previsto x realizado, alerta Slack
    databricks_entry.py        # entrada preparada, não executada aqui
  tests/                       # um arquivo por módulo
  notebooks/analise.ipynb
```

## Verificação (como o projeto prova que funciona)

- **Erlang C:** testes com valores conhecidos de tabelas publicadas e propriedades (mais pessoas nunca piora o serviço; carga zero dá espera zero).
- **Simulação:** teste que roda réplicas com semente fixa e compara com o Erlang C dentro da tolerância declarada.
- **Pipeline:** teste com um mini conjunto de linhas sintéticas e uma sessão Spark local pequena (contagens por hora conferidas à mão).
- **Previsão:** teste de que a avaliação usa só o período de teste e de que o modelo e a regra são medidos com a mesma métrica.
- **Alerta:** teste com webhook simulado (dispara acima do limite, não dispara abaixo).
- **README:** todo número vem de uma execução registrada; o plano inclui um passo que gera os números do README a partir da saída do código.

## Riscos e pré-requisitos encontrados

- **Java não está instalado** nesta máquina, e o PySpark precisa dele (JDK 17 ou 21).
- **PySpark não está instalado.** A máquina tem Python 3.15; versões muito novas do Python podem não ser aceitas pelo PySpark. O plano começa verificando isso e, se preciso, usa um ambiente virtual com versão suportada.
- O nome exato do campo de canal e a cobertura de cada ano no conjunto 311 serão confirmados no dado antes de o recorte ser congelado.
- Instalar Java e PySpark depende do Sérgio autorizar.

## Registro depois de pronto

Com o projeto concluído e verificado, registrar em `projetos.yaml` da base de currículos (Dropbox), com a fonte apontando para os arquivos do projeto. Antes de pôr em qualquer versão do currículo, perguntar ao Sérgio, porque a versão Dados já está no limite de 2 páginas.

## O que fica para quem constrói

Nomes de funções, formato dos arquivos intermediários (Parquet), detalhes dos gráficos do notebook, texto dos alertas, e o nível exato da tolerância da simulação (declarada e justificada no README).

