# memga para MATLAB e Octave

*Leia em: [English](README.en.md)*

O Método de Escolha Múltipla (MEM) escolhe um conjunto de alternativas que se completam, em vez de pegar as melhores uma a uma. Esta pasta traz o método para MATLAB e para o GNU Octave, com as mesmas opções dos pacotes em [Python](../README.md) e em [R](../r/): busca exaustiva ou algoritmo genético, as duas regras de nota e vagas por grupo.

Precisa de MATLAB R2016b ou mais novo (ou GNU Octave 7 ou mais novo). Não usa nenhuma toolbox.

## Instalação

Baixe a pasta `matlab` e adicione ao caminho do MATLAB:

```matlab
addpath('caminho/para/mem-ga/matlab')
```

## Uso

```matlab
% 2 de 8 candidatos, testando todas as duplas
resultado = memga(memga_load_example('small'), 2);
memga_print(resultado)
memga_radar(resultado)        % gráfico de radar

% Equipe de 4 entre 300, com vagas por grupo, pelo algoritmo genético
resultado = memga(memga_load_example('large'), [], 'Method', 'ga', 'Tau', 0.54, ...
    'Quotas', struct('analyst', 2, 'engineer', 1, 'manager', 1), 'Seed', 1);
resultado.team
% {'P007', 'P038', 'P192', 'P276'}, nota 0,6786
```

Para usar seus dados, monte o problema com `memga_problem(valores)`, uma matriz com uma linha por alternativa e uma coluna por critério, ou leia arquivos CSV com `memga_read_problem(pasta)`. O formato dos arquivos é o mesmo do pacote Python.

| Opção de `memga` | O que faz |
| --- | --- |
| `'Method'` | `'exhaustive'` (padrão) testa todas as combinações. `'ga'` usa o algoritmo genético, para problemas grandes. |
| `'Rule'` | `'mean'` (a regra da tese) ou `'minimum'` (critérios 2 a 2). Sem a opção, a busca exaustiva usa `'mean'` e o algoritmo genético usa `'minimum'`. |
| `'Tau'` | O corte, 0,24 por padrão. |
| `'Quotas'` | Vagas por grupo, como `struct('analyst', 2, 'manager', 1)`. |
| `'Options'` | Ajustes do algoritmo genético, de `memga_options`. |
| `'Seed'` | Semente, para repetir um resultado. |

Digite `help memga` para a lista completa. O resultado é uma struct com `team`, `score`, `ranking` (na busca exaustiva), `history` (no algoritmo genético) e `traditional`.

O algoritmo genético com as configurações padrão leva cerca de 75 segundos no exemplo grande, no Octave. Ele não prova a melhor resposta, então vale repetir com outras sementes.

## Testes

```matlab
cd tests
run_tests          % rápidos
run_tests('full')  % inclui o algoritmo genético completo no exemplo grande
```

Os valores de referência em `tests/ref` vieram da versão em Python, então as versões concordam: o ranking da regra `'mean'` é igual, e a regra `'minimum'` concorda no topo da ordem (abaixo disso, conjuntos que caem exatamente no tau podem ficar de um lado ou do outro por erro de ponto flutuante).

Os testes passaram no GNU Octave 9.4. No MATLAB, ainda não foram rodados.

## Referência

da Hora, H. R. M. e Costa, H. G. (2015). Proposta de um método multicritério para escolha múltipla. *Production*, 25(2). <https://doi.org/10.1590/0103-6513.084812>
