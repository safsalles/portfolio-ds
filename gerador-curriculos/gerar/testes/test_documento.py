import sys
from pathlib import Path

import pytest
from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from documento import montar_docx  # noqa: E402

L = lambda t: {"pt": t, "en": t, "es": t}  # noqa: E731

BASE = {
    "perfil": {"nome": "Teste", "cidade": L("Campos"), "disponibilidade": L("Remoto"),
               "telefone": "+55", "email": "a@b.c", "linkedin": "linkedin.com/in/x",
               "github": "github.com/safsalles", "lattes": "lattes.cnpq.br/1",
               "producao": {"periodicos": 10, "anais": 21, "capitulos": 1, "resumos": 2},
               "idiomas": [{"id": "pt", **L("Português")}]},
    "cargos": [{"id": "c1", "empresa": "Empresa", "titulo": L("Gerente"), "local": "RJ",
                "inicio": "2024-01", "fim": None}],
    "fatos": [
        {"id": "f1", "cargo": "c1", "tipo": "atividade", "texto": L("Fato escolhido")},
        {"id": "f2", "cargo": "c1", "tipo": "atividade", "texto": L("Fato de fora")},
        {"id": "f3", "cargo": "c1", "tipo": "resultado", "texto": L("resultado bom")},
    ],
    "formacao": [], "cursos": [], "publicacoes": [], "projetos": [],
    "competencias": [{"id": "g1", "grupo": L("Grupo"), "itens": L("SQL")}],
}
VERSAO = {"id": "dados", "titulo": L("Analista"), "resumo": L("Resumo aqui"),
          "secoes": ["resumo", "experiencia", "competencias"], "fatos": ["f1", "f3"],
          "competencias": ["g1"], "publicacoes": [], "projetos": [], "cursos": []}


def gerar(tmp_path, idioma="pt", versao=VERSAO):
    destino = tmp_path / "cv.docx"
    montar_docx(BASE, versao, idioma, destino)
    return Document(str(destino))


def textos(doc):
    return [p.text for p in doc.paragraphs]


def test_sem_tabelas_e_imagens(tmp_path):
    doc = gerar(tmp_path)
    assert doc.tables == []
    assert len(doc.inline_shapes) == 0


def test_cabecalho_rodape_vazios(tmp_path):
    secao = gerar(tmp_path).sections[0]
    assert "".join(p.text for p in secao.header.paragraphs) == ""
    assert "".join(p.text for p in secao.footer.paragraphs) == ""


def test_contato_no_corpo(tmp_path):
    corpo = "\n".join(textos(gerar(tmp_path)))
    assert "a@b.c" in corpo
    assert "github.com/safsalles" in corpo


def test_contato_sem_telefone(tmp_path):
    perfil = {k: v for k, v in BASE["perfil"].items() if k != "telefone"}
    destino = tmp_path / "cv.docx"
    montar_docx({**BASE, "perfil": perfil}, VERSAO, "pt", destino)
    contato = next(t for t in textos(Document(str(destino))) if "a@b.c" in t)
    assert contato == "Campos | Remoto | a@b.c | linkedin.com/in/x | github.com/safsalles | lattes.cnpq.br/1"


def test_lattes_no_contato(tmp_path):
    assert any("lattes.cnpq.br/1" in t and "a@b.c" in t for t in textos(gerar(tmp_path)))


def test_resumo_puxa_texto_do_fato(tmp_path):
    versao = {**VERSAO, "resumo": L("Resultados: {f3}.")}
    assert "Resultados: resultado bom." in textos(gerar(tmp_path, versao=versao))


def test_publicacao_sem_veiculo(tmp_path):
    base = {**BASE, "publicacoes": [{"id": "p1", "titulo": "Artigo", "veiculo": "", "ano": 2018}]}
    versao = {**VERSAO, "secoes": ["publicacoes"], "publicacoes": ["p1"]}
    destino = tmp_path / "cv.docx"
    montar_docx(base, versao, "pt", destino)
    assert "Artigo, 2018" in textos(Document(str(destino)))


def test_projeto_sem_link(tmp_path):
    base = {**BASE, "projetos": [{"id": "x", "nome": "Sistema", "link": "", "texto": L("Faz algo.")}]}
    versao = {**VERSAO, "secoes": ["projetos"], "projetos": ["x"]}
    destino = tmp_path / "cv.docx"
    montar_docx(base, versao, "pt", destino)
    assert "Sistema: Faz algo." in textos(Document(str(destino)))


def test_nome_do_projeto_por_idioma(tmp_path):
    projeto = {"id": "x", "nome": {"pt": "Sistema", "en": "System", "es": "Sistema"},
               "link": "", "texto": L("Faz algo.")}
    base = {**BASE, "projetos": [projeto]}
    versao = {**VERSAO, "secoes": ["projetos"], "projetos": ["x"]}
    destino = tmp_path / "cv.docx"
    montar_docx(base, versao, "en", destino)
    assert "System: Faz algo." in textos(Document(str(destino)))


def test_titulos_por_idioma(tmp_path):
    assert "Experiencia Profesional" in textos(gerar(tmp_path, "es"))


def test_secoes_na_ordem_da_versao(tmp_path):
    t = textos(gerar(tmp_path))
    assert t.index("Resumo Profissional") < t.index("Experiência Profissional") < t.index("Competências")


def test_so_fatos_da_versao(tmp_path):
    corpo = "\n".join(textos(gerar(tmp_path)))
    assert "Fato escolhido" in corpo
    assert "Fato de fora" not in corpo


def test_resultados_agrupados(tmp_path):
    assert "Resultados: resultado bom." in textos(gerar(tmp_path))


@pytest.mark.parametrize("idioma,esperado", [("es", "ene/2024 – actualidad"),
                                             ("en", "Jan 2024 – Present"),
                                             ("pt", "jan/2024 – atual")])
def test_datas_por_idioma(tmp_path, idioma, esperado):
    assert esperado in "\n".join(textos(gerar(tmp_path, idioma)))
