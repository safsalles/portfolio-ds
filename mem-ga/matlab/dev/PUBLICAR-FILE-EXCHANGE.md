# Como publicar o memga no MATLAB File Exchange

O File Exchange é a loja de códigos da MathWorks. Quem usa MATLAB acha o pacote pela busca ou pelo Add-On Explorer, dentro do próprio MATLAB. Os detalhes do site mudam, então confira as instruções atuais em <https://www.mathworks.com/matlabcentral/fileexchange/> se algo não bater.

## 0. Antes de publicar: testar no MATLAB

Os testes passaram no GNU Octave 9.4, mas **nunca foram rodados no MATLAB**. Antes de publicar, rode uma vez:

1. Abra o **MATLAB Online** em <https://matlab.mathworks.com> (grátis com uma conta MathWorks, com um limite de horas por mês).
2. Envie a pasta `matlab` para lá (arraste a pasta, ou compacte em `.zip` e use *Upload*).
3. No MATLAB, rode:

```matlab
addpath(pwd)
cd tests
run_tests
```

O esperado é `12 tests, 0 failed`. Se falhar algum, copie a mensagem e me mande, que eu corrijo.

Rode também o exemplo com o gráfico, para ver o radar:

```matlab
memga_radar(memga(memga_load_example('small'), 2))
```

## 1. Conta MathWorks

Crie ou entre na sua conta em <https://www.mathworks.com/mwaccount/>. O File Exchange usa a mesma conta, e o nome do autor é o da conta.

## 2. Publicar

Dois caminhos:

**A. Ligar ao GitHub (atualiza sozinho).** No File Exchange, clique em *Publish → Link to GitHub*, autorize o acesso e escolha o repositório. O File Exchange pega o código do GitHub, e cada nova versão que você marcar lá aparece no File Exchange. Vale confirmar se a página deixa escolher uma subpasta (`mem-ga/matlab`); se não deixar, use o caminho B ou crie um repositório só para a versão MATLAB.

**B. Enviar um arquivo.** Compacte a pasta `matlab` em um `.zip` e envie em *Publish → Upload File*.

Em qualquer caminho, preencha:
- **Título:** `memga: Multiple Choice Method for selecting sets of alternatives`
- **Resumo:** uma frase, por exemplo "Selects a set of alternatives that complement each other, by exhaustive search or genetic algorithm."
- **Descrição:** pode usar o texto do `README.en.md`.
- **Compatibilidade:** MATLAB R2016b em diante, todas as plataformas, sem toolboxes.
- **Licença:** MIT (o arquivo `license.txt` já está na pasta).
- **Tags:** `multicriteria`, `decision making`, `genetic algorithm`, `selection`.

## 3. Depois

- Coloque o link do File Exchange no README da pasta `matlab`, do Python e do R.
- Para novas versões: aumente o número da versão em `Contents.m` e no README, e publique de novo.
