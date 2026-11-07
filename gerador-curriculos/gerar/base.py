"""Leitura e validação da base de carreira e das versões de currículo."""
import re
from collections import Counter
from pathlib import Path

from ruamel.yaml import YAML

ARQUIVOS = ("perfil", "experiencias", "formacao", "publicacoes", "projetos",
            "competencias", "pendencias")
# Dados de contato que não vão para o repositório público, como o telefone.
PERFIL_LOCAL = "perfil.local.yaml"
IDIOMAS = ("pt", "en", "es")
LISTAS_DA_VERSAO = ("fatos", "competencias", "publicacoes", "projetos", "cursos")
TIPOS = ("atividade", "resultado")
REFERENCIA = re.compile(r"\{([a-z0-9-]+)\}")
TRADUZIDOS = (("cargos", "titulo"), ("cursos", "nome"), ("competencias", "grupo"),
              ("competencias", "itens"), ("projetos", "texto"), ("formacao", "titulo"))


def _ler(arquivo: Path) -> dict:
    with arquivo.open(encoding="utf-8") as f:
        return YAML(typ="safe", pure=True).load(f) or {}


def carregar_base(pasta: Path) -> dict:
    esperados = {f"{nome}.yaml" for nome in ARQUIVOS} | {PERFIL_LOCAL}
    estranhos = sorted(a.name for a in pasta.glob("*.yaml") if a.name not in esperados)
    if estranhos:
        raise ValueError(f"Arquivo inesperado em base: {', '.join(estranhos)}. "
                         "Pode ser cópia em conflito do Dropbox: resolva antes de gerar.")
    dados = {nome: _ler(pasta / f"{nome}.yaml") for nome in ARQUIVOS}
    if (pasta / PERFIL_LOCAL).exists():
        dados["perfil"].update(_ler(pasta / PERFIL_LOCAL))
    return {
        "perfil": dados["perfil"],
        "cargos": dados["experiencias"].get("cargos", []),
        "fatos": dados["experiencias"].get("fatos", []),
        "formacao": dados["formacao"].get("formacao", []),
        "cursos": dados["formacao"].get("cursos", []),
        "publicacoes": dados["publicacoes"].get("publicacoes", []),
        "projetos": dados["projetos"].get("projetos", []),
        "competencias": dados["competencias"].get("competencias", []),
        "pendencias": dados["pendencias"].get("pendencias", []),
    }


def carregar_versao(arquivo: Path) -> dict:
    versao = _ler(arquivo)
    for chave in ("titulo", "resumo"):
        versao.setdefault(chave, {})
    versao.setdefault("secoes", [])
    for chave in LISTAS_DA_VERSAO:
        versao.setdefault(chave, [])
    return versao


def carregar_versoes(pasta: Path) -> list[dict]:
    arquivos = sorted(pasta.glob("*.yaml"))
    if not arquivos:
        raise ValueError(f"Nenhuma versão encontrada em {pasta}.")
    versoes = []
    for arquivo in arquivos:
        versao = carregar_versao(arquivo)
        if versao.get("id") != arquivo.stem:
            raise ValueError(f"Arquivo {arquivo.name}: o id {versao.get('id')} difere do nome. "
                             "Pode ser cópia em conflito do Dropbox: resolva antes de gerar.")
        versoes.append(versao)
    return versoes


def _faltando(rotulo: str, texto: dict | None, idiomas=IDIOMAS) -> list[str]:
    return [f"{rotulo}: falta o texto em {i}." for i in idiomas if not (texto or {}).get(i)]


def _erros_de_fato(fato: dict, cargos: set[str]) -> list[str]:
    erros = []
    id_ = fato.get("id", "(sem id)")
    if not fato.get("fonte"):
        erros.append(f"Fato {id_}: falta a fonte.")
    if fato.get("cargo") not in cargos:
        erros.append(f"Fato {id_}: cargo {fato.get('cargo')} não existe.")
    if fato.get("tipo") not in TIPOS:
        erros.append(f"Fato {id_}: tipo {fato.get('tipo')} inválido, use {' ou '.join(TIPOS)}.")
    return erros + _faltando(f"Fato {id_}", fato.get("texto"))


def _erros_de_traducao(base: dict) -> list[str]:
    erros = []
    for grupo, campo in TRADUZIDOS:
        for item in base[grupo]:
            erros += _faltando(f"{grupo} {item['id']}, {campo}", item.get(campo))
    perfil = base["perfil"]
    for campo in ("cidade", "disponibilidade"):
        erros += _faltando(f"Perfil, {campo}", perfil.get(campo))
    for item in perfil.get("idiomas", []):
        erros += _faltando(f"Perfil, idioma {item.get('id')}", item)
    return erros


def _erros_de_textos_da_versao(versao: dict, fatos: set[str]) -> list[str]:
    erros = []
    idiomas = versao.get("idiomas", IDIOMAS)
    for campo in ("titulo", "resumo"):
        erros += _faltando(f"Versão {versao['id']}, {campo}", versao[campo], idiomas)
    for texto in versao["resumo"].values():
        for id_ in REFERENCIA.findall(texto):
            if id_ not in fatos:
                erros.append(f"Versão {versao['id']}, resumo: fato {id_} não existe.")
    return erros


def validar(base: dict, versoes: list[dict]) -> list[str]:
    erros = []
    cargos = {c["id"] for c in base["cargos"]}
    for fato in base["fatos"]:
        erros += _erros_de_fato(fato, cargos)
    erros += _erros_de_traducao(base)

    grupos = ("cargos", "fatos", "cursos", "publicacoes", "projetos", "competencias",
              "formacao", "pendencias")
    contagem = Counter(item["id"] for g in grupos for item in base[g])
    erros += [f"id repetido na base: {id_}." for id_, n in contagem.items() if n > 1]

    pendentes = {p["id"] for p in base["pendencias"]}
    fatos = {f["id"] for f in base["fatos"]}
    for versao in versoes:
        erros += _erros_de_textos_da_versao(versao, fatos)
        for chave in LISTAS_DA_VERSAO:
            existentes = {item["id"] for item in base[chave]}
            for id_ in versao[chave]:
                if id_ in pendentes:
                    erros.append(f"Versão {versao['id']}: {id_} é pendência e não pode entrar.")
                elif id_ not in existentes:
                    erros.append(f"Versão {versao['id']}: {id_} não existe em {chave}.")
    return erros
