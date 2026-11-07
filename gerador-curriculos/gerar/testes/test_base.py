import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from base import carregar_base, carregar_versao, carregar_versoes, validar  # noqa: E402

PERFIL = """
nome: Teste
email: a@b.c
cidade: {pt: C, en: C, es: C}
disponibilidade: {pt: R, en: R, es: R}
idiomas:
  - {id: pt, pt: P, en: P, es: P}
"""
EXPERIENCIAS = """
cargos:
  - id: cargo-a
    empresa: Empresa
    titulo: {pt: Cargo, en: Role, es: Puesto}
    inicio: 2024-01
    fim: 2025-01
fatos:
  - id: fato-a
    cargo: cargo-a
    tipo: atividade
    temas: [dados]
    fonte: teste
    texto: {pt: Fez, en: Did, es: Hizo}
"""


def escrever_base(pasta: Path, **trocas: str) -> Path:
    arquivos = {
        "perfil": PERFIL,
        "experiencias": EXPERIENCIAS,
        "formacao": "formacao: []\ncursos: []\n",
        "publicacoes": "publicacoes: []\n",
        "projetos": "projetos: []\n",
        "competencias": "competencias: []\n",
        "pendencias": "pendencias:\n  - id: pend-a\n    descricao: algo\n",
    }
    arquivos.update(trocas)
    for nome, texto in arquivos.items():
        (pasta / f"{nome}.yaml").write_text(texto, encoding="utf-8")
    return pasta


def test_perfil_local_completa_o_perfil(tmp_path):
    escrever_base(tmp_path)
    (tmp_path / "perfil.local.yaml").write_text('telefone: "+55 11 9"\n', encoding="utf-8")
    perfil = carregar_base(tmp_path)["perfil"]
    assert perfil["telefone"] == "+55 11 9"
    assert perfil["email"] == "a@b.c"


def test_sem_perfil_local_nao_tem_telefone(tmp_path):
    assert "telefone" not in carregar_base(escrever_base(tmp_path))["perfil"]


def versao(fatos: list[str]) -> dict:
    texto = {"pt": "T", "en": "T", "es": "T"}
    return {"id": "dados", "titulo": dict(texto), "resumo": dict(texto), "secoes": [],
            "fatos": fatos, "competencias": [], "publicacoes": [], "projetos": [], "cursos": []}


def test_versao_sem_resumo_em_idioma(tmp_path):
    base = carregar_base(escrever_base(tmp_path))
    v = versao([])
    v["resumo"]["es"] = ""
    assert any("dados" in e and "resumo" in e and "es" in e for e in validar(base, [v]))


def test_versao_so_em_pt_nao_exige_outros_idiomas(tmp_path):
    base = carregar_base(escrever_base(tmp_path))
    v = versao([])
    v["idiomas"] = ["pt"]
    v["resumo"] = {"pt": "T"}
    assert validar(base, [v]) == []


def test_curso_sem_traducao(tmp_path):
    formacao = "formacao: []\ncursos:\n  - {id: c1, nome: {pt: Curso}, instituicao: X, ano: 2020}\n"
    base = carregar_base(escrever_base(tmp_path, formacao=formacao))
    assert any("c1" in e and "en" in e for e in validar(base, []))


def test_perfil_sem_traducao(tmp_path):
    base = carregar_base(escrever_base(tmp_path, perfil=PERFIL.replace(", es: C}", "}", 1)))
    assert any("cidade" in e and "es" in e for e in validar(base, []))


def test_tipo_invalido(tmp_path):
    texto = EXPERIENCIAS.replace("tipo: atividade", "tipo: resultados")
    base = carregar_base(escrever_base(tmp_path, experiencias=texto))
    assert any("fato-a" in e and "tipo" in e for e in validar(base, []))


def test_resumo_cita_fato_inexistente(tmp_path):
    base = carregar_base(escrever_base(tmp_path))
    v = versao([])
    v["resumo"]["pt"] = "Resultados: {fato-x}."
    assert any("fato-x" in e and "dados" in e for e in validar(base, [v]))


def test_sem_versoes_e_erro(tmp_path):
    with pytest.raises(ValueError, match="Nenhuma versão"):
        carregar_versoes(tmp_path)


def test_versao_em_conflito(tmp_path):
    (tmp_path / "gestao.yaml").write_text("id: gestao\n", encoding="utf-8")
    copia = tmp_path / "gestao (conflicted copy).yaml"
    copia.write_text("id: gestao\n", encoding="utf-8")
    with pytest.raises(ValueError, match="conflicted copy"):
        carregar_versoes(tmp_path)


def test_base_valida_sem_erros(tmp_path):
    base = carregar_base(escrever_base(tmp_path))
    assert validar(base, [versao(["fato-a"])]) == []


def test_fato_sem_traducao(tmp_path):
    texto = EXPERIENCIAS.replace(", es: Hizo", "")
    base = carregar_base(escrever_base(tmp_path, experiencias=texto))
    erros = validar(base, [])
    assert any("fato-a" in e and "es" in e for e in erros)


def test_fato_sem_fonte(tmp_path):
    texto = EXPERIENCIAS.replace("    fonte: teste\n", "")
    base = carregar_base(escrever_base(tmp_path, experiencias=texto))
    assert any("fato-a" in e and "fonte" in e for e in validar(base, []))


def test_id_repetido(tmp_path):
    repetido = EXPERIENCIAS + EXPERIENCIAS[EXPERIENCIAS.index("  - id: fato-a"):]
    base = carregar_base(escrever_base(tmp_path, experiencias=repetido))
    assert any("fato-a" in e and "repetido" in e for e in validar(base, []))


def test_versao_cita_id_inexistente(tmp_path):
    base = carregar_base(escrever_base(tmp_path))
    erros = validar(base, [versao(["fato-x"])])
    assert any("fato-x" in e and "dados" in e for e in erros)


def test_versao_cita_pendencia(tmp_path):
    base = carregar_base(escrever_base(tmp_path))
    erros = validar(base, [versao(["pend-a"])])
    assert any("pend-a" in e and "pendência" in e for e in erros)


def test_copia_em_conflito(tmp_path):
    escrever_base(tmp_path)
    (tmp_path / "experiencias (conflicted copy).yaml").write_text("x: 1", encoding="utf-8")
    with pytest.raises(ValueError, match="conflicted copy"):
        carregar_base(tmp_path)


def test_carregar_versao(tmp_path):
    arquivo = tmp_path / "dados.yaml"
    arquivo.write_text("id: dados\nfatos: [fato-a]\n", encoding="utf-8")
    v = carregar_versao(arquivo)
    assert v["id"] == "dados"
    assert v["fatos"] == ["fato-a"]
    assert v["cursos"] == []
