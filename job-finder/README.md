# Job Finder

*Leia em: [English](README.en.md)*

Bot que busca vagas em várias fontes, separa por categoria, prioriza futebol, as empresas que você avaliou bem e as grandes empresas e envia as vagas novas por e-mail, todos os dias, em um horário agendado.

## Como funciona

1. **Coleta** vagas em cinco fontes:
   - [Remotar](https://remotar.com.br/): vagas remotas no Brasil, lidas com o Playwright.
   - [Gupy](https://portal.gupy.io/): vagas brasileiras, pela API pública do portal.
   - LinkedIn: pela busca pública de vagas, **sem login**, para a conta não correr risco de ser banida. São poucas buscas por dia, com pausa entre elas; se o LinkedIn bloquear, o bot segue com as outras fontes.
   - Empresas de dados de futebol (Hudl, Genius Sports, Kitman Labs, Sportradar): pelas APIs públicas dos sistemas de vagas delas, que só listam vagas abertas.
   - [Jobs In Football](https://jobsinfootball.com/): vagas de clubes do mundo todo, com o Playwright.
2. **Classifica** cada vaga pelo título em uma categoria: Analytics Futebol, Análise de Dados, Analista de BI, Analista/Assistente Administrativo ou Outras (Engenharia de Produção/Planejamento). Vagas fora delas, estágios e títulos com termos de exclusão são descartados.
3. **Filtra pelo local**:
   - Vagas gerais: só remotas.
   - Vagas de futebol: no Brasil (mesmo presenciais) ou remotas que aceitem quem mora no Brasil. O bot lê a descrição da vaga: se ela pede residência ou permissão de trabalho nos EUA, Reino Unido ou Europa, sai; se cita Brasil, LATAM ou "anywhere", entra; se não diz nada, entra com um aviso para conferir.
4. **Prioriza** no e-mail: futebol, depois as empresas que você marcou como "quero" ou "quero muito", depois grandes empresas, depois o resto e, no fim, as empresas "meh". Empresas marcadas como "evitar" não aparecem. Dentro de cada bloco, as vagas ficam agrupadas por categoria, das mais recentes para as mais antigas.
5. **Enriquece** cada vaga:
   - **Afinidade** entre parênteses depois do título, por exemplo "(75% de afinidade)": das ferramentas e técnicas que a vaga cita (SQL, Power BI, Spark, AWS...), quantas estão nas suas competências, lidas de [`gerador-curriculos/base/competencias.yaml`](../gerador-curriculos/base/competencias.yaml). Logo abaixo vem o que falta. Vaga sem descrição (caso do Remotar) ou que cita menos de 2 itens fica sem %.
   - **Uma linha sobre a empresa** embaixo do link: vem do `empresas.txt` ou, se a empresa não estiver lá, da Wikipédia (guardada em cache para não buscar de novo).
   - **Empresas novas para você avaliar**: no fim do e-mail, as empresas que ainda não estão no `empresas.txt`, numa linha pronta para colar lá.
6. **Lembra** das vagas já enviadas (`vagas_vistas.json`), para cada vaga chegar uma vez só. Se nada for novo, nenhum e-mail é enviado.

### Sua avaliação das empresas

[`empresas.txt`](empresas.txt) tem uma empresa por linha no formato `Nome | nota | por que a empresa é maneira`. As notas são `quero muito`, `quero`, `ok`, `meh` e `evitar`. A comparação ignora maiúsculas e acentos e procura o nome inteiro no nome da empresa da vaga.

### O que é "grande empresa"

É quem está em [`empresas_grandes.txt`](empresas_grandes.txt): uma lista editável, uma empresa por linha, montada a partir do GPTW Brasil, do LinkedIn Top Companies Brasil, das maiores empresas do Brasil e do mundo e de multinacionais que contratam remoto no Brasil. A comparação ignora maiúsculas e acentos e procura a palavra inteira no nome da empresa ("itau" casa com "Itaú Unibanco").

## Estrutura

| Arquivo | O que faz |
|---|---|
| `job_finder.py` | Junta tudo: coleta, classifica, filtra as novas e envia |
| `fontes/` | Um módulo por fonte de vagas |
| `classificacao.py` | Categorias, futebol, local e prioridade |
| `empresas.py` | Sua avaliação das empresas e a descrição de uma linha |
| `afinidade.py` | Afinidade entre as suas competências e a vaga |
| `memoria.py` | Vagas já enviadas |
| `email_vagas.py` | Monta e envia o e-mail |
| `empresas.txt` | Sua avaliação das empresas |
| `empresas_grandes.txt` | Lista de grandes empresas |
| `tests/` | Testes da classificação |

## Como rodar

Instale as dependências:

```bash
pip install -r requirements.txt
playwright install chromium
```

Copie `config.example.txt` para `~\Desktop\aux portfolio\job finder\config_vagas.txt` e preencha com os seus dados. Esse arquivo fica fora do repositório para as credenciais não irem para o GitHub. O campo `SENHA_APP` usa uma senha de app do Google, não a senha normal da conta. A memória das vagas enviadas fica na mesma pasta.

Para testar sem enviar e-mail nem gravar a memória (salva uma prévia em `previa_email.html`, na mesma pasta do config):

```bash
python job_finder.py --sem-email
```

Para rodar de verdade:

```bash
python job_finder.py
```

Para rodar todo dia, agende o `rodar_bot.bat` no Agendador de Tarefas do Windows. Os testes rodam com `python -m pytest tests`.

## Personalização

- Termos de busca de cada fonte: no começo de `job_finder.py`.
- Categorias, termos de exclusão e regras de local: em `classificacao.py`.
- Empresas de futebol monitoradas: em `fontes/empresas_futebol.py`.
- Grandes empresas: em `empresas_grandes.txt`.
- Sua nota de cada empresa: em `empresas.txt`.
- Ferramentas consideradas na afinidade: em `afinidade.py`.

## Limitações

- O LinkedIn pode bloquear a busca pública em alguns dias. Quando isso acontece, as vagas dele ficam para a próxima rodada.
- A regra de local das vagas de futebol lê a descrição em busca de palavras-chave, então pode errar em descrições pouco claras. Por isso as remotas sem país definido vêm marcadas para conferir.
- A afinidade compara palavras, não entende contexto: uma vaga que cita AWS como "desejável" conta igual a uma que exige. É um guia rápido, não uma nota.
- Os sites mudam: se uma fonte mudar o layout ou a API, ela para de trazer vagas até o código ser ajustado. As outras continuam funcionando.
