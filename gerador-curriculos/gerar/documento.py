"""Monta o documento do currículo: uma coluna, só texto, contato no corpo."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from base import REFERENCIA

COR = RGBColor(0x1F, 0x3A, 0x5F)
FONTE = "Calibri"

TITULOS = {
    "resumo": {"pt": "Resumo Profissional", "en": "Professional Summary", "es": "Resumen Profesional"},
    "competencias": {"pt": "Competências", "en": "Skills", "es": "Competencias"},
    "experiencia": {"pt": "Experiência Profissional", "en": "Professional Experience", "es": "Experiencia Profesional"},
    "projetos": {"pt": "Projetos", "en": "Projects", "es": "Proyectos"},
    "formacao": {"pt": "Formação", "en": "Education", "es": "Formación"},
    "cursos": {"pt": "Cursos e Certificações", "en": "Courses and Certifications", "es": "Cursos y Certificaciones"},
    "idiomas": {"pt": "Idiomas", "en": "Languages", "es": "Idiomas"},
    "publicacoes": {"pt": "Publicações", "en": "Publications", "es": "Publicaciones"},
}
MESES = {
    "pt": "jan fev mar abr mai jun jul ago set out nov dez".split(),
    "en": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(),
    "es": "ene feb mar abr may jun jul ago sep oct nov dic".split(),
}
ATUAL = {"pt": "atual", "en": "Present", "es": "actualidad"}
RESULTADOS = {"pt": "Resultados", "en": "Results", "es": "Resultados"}
HORAS = {"pt": "horas", "en": "hours", "es": "horas"}
PRODUCAO = {
    "pt": "Produção científica: {periodicos} artigos em periódicos, {anais} trabalhos em anais, {capitulos} capítulo de livro e {resumos} resumos expandidos. Lista completa: {lattes}",
    "en": "Scientific output: {periodicos} journal articles, {anais} conference papers, {capitulos} book chapter and {resumos} extended abstracts. Full list: {lattes}",
    "es": "Producción científica: {periodicos} artículos en revistas, {anais} trabajos en congresos, {capitulos} capítulo de libro y {resumos} resúmenes extendidos. Lista completa: {lattes}",
}


def _data(valor: str | None, idioma: str) -> str:
    if valor is None:
        return ATUAL[idioma]
    ano, mes = str(valor).split("-")
    nome = MESES[idioma][int(mes) - 1]
    return f"{nome} {ano}" if idioma == "en" else f"{nome}/{ano}"


def _preparar_estilos(doc) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = Pt(10)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.0

    titulo = doc.styles["Heading 1"]
    titulo.font.name = FONTE
    titulo.font.size = Pt(11)
    titulo.font.bold = True
    titulo.font.color.rgb = COR
    for tema in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        titulo.element.rPr.rFonts.attrib.pop(qn(f"w:{tema}"), None)
    titulo.paragraph_format.space_before = Pt(7)
    titulo.paragraph_format.space_after = Pt(2)

    lista = doc.styles["List Bullet"]
    lista.paragraph_format.space_after = Pt(1)
    lista.paragraph_format.keep_together = True

    secao = doc.sections[0]
    secao.page_width, secao.page_height = Cm(21), Cm(29.7)
    secao.left_margin = secao.right_margin = Cm(1.8)
    secao.top_margin = secao.bottom_margin = Cm(1.5)


def _titulo_secao(doc, texto: str) -> None:
    paragrafo = doc.add_paragraph(texto, style="Heading 1")
    borda = OxmlElement("w:pBdr")
    linha = OxmlElement("w:bottom")
    for chave, valor in (("val", "single"), ("sz", "6"), ("space", "1"), ("color", "1F3A5F")):
        linha.set(qn(f"w:{chave}"), valor)
    borda.append(linha)
    paragrafo._p.get_or_add_pPr().append(borda)


def _rotulado(doc, rotulo: str, texto: str) -> None:
    paragrafo = doc.add_paragraph()
    paragrafo.add_run(f"{rotulo}: ").bold = True
    paragrafo.add_run(texto)


def _cabecalho(doc, base: dict, versao: dict, idioma: str) -> None:
    perfil = base["perfil"]
    nome = doc.add_paragraph()
    nome.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = nome.add_run(perfil["nome"])
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = COR

    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.add_run(versao["titulo"][idioma]).bold = True

    contato = [perfil["cidade"][idioma], perfil["disponibilidade"][idioma], perfil.get("telefone"),
               perfil["email"], perfil["linkedin"], perfil["github"], perfil["lattes"]]
    linha = doc.add_paragraph(" | ".join(c for c in contato if c))
    linha.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _resumo(doc, base, versao, idioma) -> None:
    fatos = {f["id"]: f for f in base["fatos"]}
    texto = REFERENCIA.sub(lambda m: fatos[m[1]]["texto"][idioma], versao["resumo"][idioma])
    doc.add_paragraph(texto)


def _competencias(doc, base, versao, idioma) -> None:
    grupos = {c["id"]: c for c in base["competencias"]}
    for id_ in versao["competencias"]:
        _rotulado(doc, grupos[id_]["grupo"][idioma], grupos[id_]["itens"][idioma])


def _linha_do_cargo(cargo: dict, idioma: str) -> str:
    partes = [cargo["empresa"]]
    if cargo.get("setor"):
        partes.append(cargo["setor"][idioma])
    partes.append(cargo["local"])
    partes.append(f"{_data(cargo['inicio'], idioma)} – {_data(cargo['fim'], idioma)}")
    linha = " | ".join(partes)
    if cargo.get("nota"):
        linha += f" ({cargo['nota'][idioma]})"
    return linha


def _experiencia(doc, base, versao, idioma) -> None:
    fatos = {f["id"]: f for f in base["fatos"]}
    escolhidos = [fatos[id_] for id_ in versao["fatos"]]
    ordem = list(dict.fromkeys(f["cargo"] for f in escolhidos))
    cargos = {c["id"]: c for c in base["cargos"]}
    for id_cargo in ordem:
        cargo = cargos[id_cargo]
        titulo = doc.add_paragraph()
        titulo.paragraph_format.space_before = Pt(4)
        titulo.paragraph_format.keep_with_next = True
        titulo.add_run(cargo["titulo"][idioma]).bold = True
        linha = doc.add_paragraph()
        linha.paragraph_format.keep_with_next = True
        linha.add_run(_linha_do_cargo(cargo, idioma)).italic = True

        do_cargo = [f for f in escolhidos if f["cargo"] == id_cargo]
        for fato in do_cargo:
            if fato["tipo"] == "atividade":
                doc.add_paragraph(fato["texto"][idioma], style="List Bullet")
        resultados = [f["texto"][idioma] for f in do_cargo if f["tipo"] == "resultado"]
        if resultados:
            paragrafo = doc.add_paragraph(style="List Bullet")
            paragrafo.add_run(f"{RESULTADOS[idioma]}: ").bold = True
            paragrafo.add_run("; ".join(resultados) + ".")


def _projetos(doc, base, versao, idioma) -> None:
    projetos = {p["id"]: p for p in base["projetos"]}
    for id_ in versao["projetos"]:
        projeto = projetos[id_]
        nome = projeto["nome"][idioma] if isinstance(projeto["nome"], dict) else projeto["nome"]
        _rotulado(doc, nome, f"{projeto['texto'][idioma]} {projeto.get('link', '')}".strip())


def _formacao(doc, base, versao, idioma) -> None:
    for item in base["formacao"]:
        paragrafo = doc.add_paragraph(style="List Bullet")
        paragrafo.add_run(item["titulo"][idioma]).bold = True
        paragrafo.add_run(f" – {item['instituicao']}, {item['inicio']}–{item['fim']}")


def _cursos(doc, base, versao, idioma) -> None:
    cursos = {c["id"]: c for c in base["cursos"]}
    for id_ in versao["cursos"]:
        curso = cursos[id_]
        linha = f"{curso['nome'][idioma]} – {curso['instituicao']}, {curso['ano']}"
        if curso.get("horas"):
            linha += f" ({curso['horas']} {HORAS[idioma]})"
        doc.add_paragraph(linha, style="List Bullet")


def _idiomas(doc, base, versao, idioma) -> None:
    doc.add_paragraph(" | ".join(i[idioma] for i in base["perfil"]["idiomas"]))


def _publicacoes(doc, base, versao, idioma) -> None:
    perfil = base["perfil"]
    doc.add_paragraph(PRODUCAO[idioma].format(lattes=perfil["lattes"], **perfil["producao"]))
    publicacoes = {p["id"]: p for p in base["publicacoes"]}
    for id_ in versao["publicacoes"]:
        item = publicacoes[id_]
        origem = f" – {item['veiculo']}" if item.get("veiculo") else ""
        doc.add_paragraph(f"{item['titulo']}{origem}, {item['ano']}", style="List Bullet")


SECOES = {"resumo": _resumo, "competencias": _competencias, "experiencia": _experiencia,
          "projetos": _projetos, "formacao": _formacao, "cursos": _cursos,
          "idiomas": _idiomas, "publicacoes": _publicacoes}


def montar_docx(base: dict, versao: dict, idioma: str, destino: Path) -> None:
    doc = Document()
    _preparar_estilos(doc)
    doc.core_properties.author = base["perfil"]["nome"]
    doc.core_properties.title = f"{base['perfil']['nome']} – {versao['titulo'][idioma]}"
    _cabecalho(doc, base, versao, idioma)
    for secao in versao["secoes"]:
        _titulo_secao(doc, TITULOS[secao][idioma])
        SECOES[secao](doc, base, versao, idioma)
    doc.save(str(destino))
