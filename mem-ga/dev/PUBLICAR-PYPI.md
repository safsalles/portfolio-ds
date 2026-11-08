# Como publicar o memga no PyPI

O PyPI é o repositório oficial de pacotes Python. Depois de publicar, qualquer pessoa instala com `pip install memga`.

## 0. Antes de começar

- O nome `memga` estava livre no PyPI em 08/11/2026. Quem publica primeiro fica com ele, então não demore muito.
- **Uma versão publicada não pode ser apagada nem reenviada.** Se errar, é preciso subir uma versão nova (`1.1.1`). Por isso vale testar no TestPyPI antes.
- O e-mail do `pyproject.toml` (`safsalles@hotmail.com`) vira público na página do pacote.

## 1. Criar as contas e o token

1. Crie uma conta no PyPI: <https://pypi.org/account/register/>. Ative a **verificação em dois passos** (o PyPI exige).
2. Crie uma conta separada no TestPyPI, que é um PyPI de ensaio: <https://test.pypi.org/account/register/>. As contas não são ligadas.
3. Em cada site, vá em *Account settings → API tokens → Add API token*. Para o primeiro envio, escolha o escopo *Entire account* (o escopo por projeto só existe depois que o projeto existe).
4. Copie o token (começa com `pypi-`). **Ele aparece uma vez só.** Guarde em um gerenciador de senhas e **nunca cole o token em chat, e-mail ou arquivo do projeto.**

## 2. Gerar os arquivos

Em um ambiente virtual com as ferramentas, na pasta `mem-ga`:

```bash
pip install build twine
python -m build
twine check dist/*
```

Isso cria a pasta `dist/` com dois arquivos: `memga-1.1.0.tar.gz` e `memga-1.1.0-py3-none-any.whl`. O `twine check` precisa mostrar `PASSED` nos dois.

## 3. Ensaio no TestPyPI

```bash
twine upload --repository testpypi dist/*
```

O `twine` pergunta o usuário e a senha: use `__token__` como usuário e o token do **TestPyPI** como senha. Depois teste a instalação em um ambiente limpo:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ memga
python -c "from memga import memga, load_example; print(memga(load_example('small'), size=2))"
```

O `--extra-index-url` é para o numpy e o matplotlib virem do PyPI de verdade.

## 4. Publicar de verdade

```bash
twine upload dist/*
```

Usuário `__token__` e o token do **PyPI** como senha. A página fica em <https://pypi.org/project/memga/>. Teste:

```bash
pip install memga
```

## 5. Depois

- Crie uma *release* no GitHub com a tag `py-v1.1.0`, para ligar o código à versão.
- Troque o token de conta inteira por um token só do projeto `memga` (em *Account settings → API tokens*), e apague o antigo.
- Para novas versões: aumente `version` no `pyproject.toml` (e `__version__` em `src/memga/__init__.py`), apague a pasta `dist/` antiga, gere de novo e faça o `twine upload`.
- Opcional: o PyPI aceita *Trusted Publishing* pelo GitHub Actions, que publica sem token. Vale configurar quando você publicar com frequência.
