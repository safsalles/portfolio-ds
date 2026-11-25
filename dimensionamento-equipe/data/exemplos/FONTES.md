# Fontes dos dados de exemplo / Data sources

Estes arquivos existem para o projeto e o app funcionarem **sem baixar nada**. São extratos derivados e pequenos, não os arquivos originais.
*These files let the project and the app run **without any download**. They are small derived extracts, not the original files.*

## `technion_chamadas.csv.gz` — call center "Anonymous Bank" (Technion SEE Center)

- **O que é:** registro de todas as ligações de um call center de banco em Israel, de 01/01/1999 a 31/12/1999, com a hora de entrada, a espera na fila, o resultado (atendida, desistiu) e o tempo real de atendimento. É um call center pequeno: 8 posições de atendimento, segundo a documentação.
- **Por que foi usado:** é uma das poucas bases públicas com **tempos reais de atendimento**, o que permite ajustar distribuições a dado de verdade (o NYC 311 só traz chegadas) e comparar a simulação com a espera que o banco de fato teve.
- **Limites:** é de 1999, de um banco em Israel, e parte dos clientes desiste da fila (o simulador do projeto não modela abandono). Não representa o NYC 311.
- **Fonte:** Technion SEE Center, base "Anonymous Bank". Documentação de Ilan Guedj e Avi Mandelbaum (9 de fevereiro de 2000). Página do repositório de dados: https://seelab.net.technion.ac.il/data/ — arquivo original: `AnonymousBank.rar` (10,6 MB), em https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/
- **Termos:** os dados são de uso livre; quem os usar deve avisar o professor Avi Mandelbaum e citar a fonte. **Aviso enviado em 25/11/2026** por e-mail ao professor (com cópia à equipe SEE); nenhuma resposta registrada até aqui. Se ele pedir para não redistribuir o extrato, este arquivo será removido e o projeto passará a apontar para o site do Technion.
- **O que o extrato contém:** `date`, `entry_s` (segundo do dia em que a ligação entrou), `type`, `outcome` (AGENT, HANG ou PHANTOM), `q_time_s` (espera na fila, s) e `ser_time_s` (duração do atendimento, s). **Não contém** o número do cliente nem o nome dos atendentes, que existem nos arquivos originais.
- **Como foi gerado:** `scripts/preparar_technion.py` sobre os 12 arquivos mensais. 444.448 ligações; 353.143 atendidas, 87.706 desistências, 3.599 "fantasma" (ligações virtuais que a própria documentação manda ignorar). Algumas linhas separam campos por espaços em vez de tabulação; o preparo as aceita.

## `nyc311_horario.csv.gz` — NYC 311 (chegadas por hora)

- **O que é:** contagem de chamadas de telefone por hora ao NYC 311 em 2024 e 2025, agregada pelo pipeline PySpark do projeto.
- **Fonte:** NYC Open Data, "311 Service Requests from 2010 to Present" (identificador `erm2-nwe9`), https://data.cityofnewyork.us/ — filtrado pelo canal telefone (`open_data_channel_type = PHONE`).
- **Nota:** a hora de abertura do chamado é tratada como hora de chegada do contato (aproximação).

## Atenção ao misturar as fontes

O cenário padrão do app usa as **chegadas do NYC 311** e o **atendimento do Technion**. As duas bases não têm relação entre si; o único elo real com o banco é a distribuição do tempo de atendimento.
