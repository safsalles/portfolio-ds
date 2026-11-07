import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arquivar import arquivar, publicar  # noqa: E402
from checar import checar_pdf, numeros_fora_da_base  # noqa: E402
from gerar import converter_pdf, main  # noqa: E402

AGORA = datetime(2026, 11, 6, 15, 30, 0)


def test_arquivar_move_com_data(tmp_path):
    saida, historico = tmp_path / "saida", tmp_path / "historico"
    saida.mkdir()
    (saida / "a.pdf").write_bytes(b"x")
    arquivar(saida, historico, AGORA)
    assert (historico / "2026-11-06_153000" / "a.pdf").exists()
    assert list(saida.glob("*.pdf")) == []


def test_arquivar_sem_pdfs_nao_cria_pasta(tmp_path):
    saida, historico = tmp_path / "saida", tmp_path / "historico"
    saida.mkdir()
    arquivar(saida, historico, AGORA)
    assert not historico.exists()


def test_arquivar_arquivo_travado(tmp_path):
    saida, historico = tmp_path / "saida", tmp_path / "historico"
    saida.mkdir()
    (saida / "a.pdf").write_bytes(b"x")
    (saida / "b.pdf").write_bytes(b"x")
    with open(saida / "b.pdf", "rb"):
        with pytest.raises(PermissionError, match="b.pdf"):
            arquivar(saida, historico, AGORA)
    assert (saida / "a.pdf").exists()
    assert (saida / "b.pdf").exists()
    assert not historico.exists()


def test_checar_pdf_tres_paginas(tmp_path):
    pdf = tmp_path / "longo.pdf"
    escritor = PdfWriter()
    for _ in range(3):
        escritor.add_blank_page(width=200, height=200)
    escritor.write(str(pdf))
    assert any("longo.pdf" in e and "3 páginas" in e for e in checar_pdf(pdf, {}))


def test_checar_numero_fora_da_base():
    base = {"fatos": [{"texto": {"pt": "+1,2 p.p. e 15.000 SKUs"}}]}
    assert numeros_fora_da_base("+9,9 p.p.", base) == ["9,9"]


@pytest.mark.parametrize("texto", ["+1.2 p.p.", "+1,2 p.p.", "15,000", "15.000"])
def test_numero_com_ponto_ou_virgula_e_o_mesmo(texto):
    base = {"fatos": [{"texto": {"pt": "+1,2 p.p. e 15.000 SKUs"}}]}
    assert numeros_fora_da_base(texto, base) == []


def test_pendencia_nao_conta_como_numero_confirmado():
    base = {"fatos": [{"texto": {"pt": "1 p.p."}}],
            "pendencias": [{"id": "p", "descricao": "+16,7% de produtividade"}]}
    assert numeros_fora_da_base("+16,7%", base) == ["16,7"]


def test_decimal_nao_vira_inteiro():
    base = {"fatos": [{"texto": {"pt": "+1,2 p.p. e 12 lojas"}}]}
    assert numeros_fora_da_base("+1,5 p.p.", base) == ["1,5"]
    base = {"fatos": [{"texto": {"pt": "+1,2 p.p."}}]}
    assert numeros_fora_da_base("+12 p.p.", base) == ["12"]


def test_publicar_falha_restaura_saida(tmp_path, monkeypatch):
    saida, historico, novos = tmp_path / "saida", tmp_path / "historico", tmp_path / "novos"
    saida.mkdir()
    novos.mkdir()
    for nome in "abc":
        (saida / f"{nome}.pdf").write_bytes(b"velho")
        (novos / f"{nome}.pdf").write_bytes(b"novo")
    copiar = shutil.copy2
    chamadas = []

    def falha_no_terceiro(origem, destino):
        chamadas.append(origem)
        if len(chamadas) == 3:
            raise OSError("disco cheio")
        return copiar(origem, destino)

    monkeypatch.setattr(shutil, "copy2", falha_no_terceiro)
    with pytest.raises(OSError):
        publicar(novos, saida, historico, AGORA)
    assert sorted(a.name for a in saida.iterdir()) == ["a.pdf", "b.pdf", "c.pdf"]
    assert all(a.read_bytes() == b"velho" for a in saida.iterdir())
    assert not historico.exists()


def test_publicar_guarda_antigos_e_coloca_novos(tmp_path):
    saida, historico, novos = tmp_path / "saida", tmp_path / "historico", tmp_path / "novos"
    saida.mkdir()
    novos.mkdir()
    (saida / "a.pdf").write_bytes(b"velho")
    (novos / "a.pdf").write_bytes(b"novo")
    publicar(novos, saida, historico, AGORA)
    assert (saida / "a.pdf").read_bytes() == b"novo"
    assert (historico / "2026-11-06_153000" / "a.pdf").read_bytes() == b"velho"


def test_gerar_sem_versoes_nao_esvazia_saida(tmp_path, capsys):
    raiz = raiz_invalida(tmp_path)
    (raiz / "versoes" / "dados.yaml").unlink()
    assert main(raiz) == 1
    assert "Nenhuma versão" in capsys.readouterr().out
    assert [a.name for a in (raiz / "saida").iterdir()] == ["antigo.pdf"]


def raiz_invalida(tmp_path) -> Path:
    raiz = tmp_path / "Carreira"
    shutil.copytree(Path(__file__).resolve().parents[2] / "base", raiz / "base")
    (raiz / "versoes").mkdir()
    (raiz / "versoes" / "dados.yaml").write_text("id: dados\nfatos: [nao-existe]\n", encoding="utf-8")
    (raiz / "saida").mkdir()
    (raiz / "saida" / "antigo.pdf").write_bytes(b"x")
    return raiz


def test_gerar_para_com_base_invalida(tmp_path, capsys):
    raiz = raiz_invalida(tmp_path)
    assert main(raiz) == 1
    assert "nao-existe" in capsys.readouterr().out
    assert [a.name for a in (raiz / "saida").iterdir()] == ["antigo.pdf"]


@pytest.mark.skipif(shutil.which("powershell") is None, reason="sem PowerShell")
def test_pdf_em_caminho_com_acento(tmp_path):
    pasta = tmp_path / "Sérgio teste"
    pasta.mkdir()
    doc = Document()
    doc.add_paragraph("Olá")
    doc.save(str(pasta / "cv.docx"))
    converter_pdf(pasta)
    assert (pasta / "cv.pdf").exists()


def _simular(monkeypatch, word: bool, soffice: str | None, word_falha: bool = False):
    import gerar
    chamadas = []

    def rodar(cmd, **_):
        chamadas.append(cmd)
        if cmd[0] == "powershell":
            return subprocess.CompletedProcess(cmd, 1 if word_falha else 0, "", "Word ausente")
        pasta = Path(cmd[cmd.index("--outdir") + 1])
        for docx in pasta.glob("*.docx"):
            docx.with_suffix(".pdf").write_bytes(b"%PDF")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(gerar.subprocess, "run", rodar)
    monkeypatch.setattr(gerar, "_tem_word", lambda: word)
    monkeypatch.setattr(gerar, "_achar_libreoffice", lambda: soffice)
    return chamadas


def _pasta_com_docx(tmp_path):
    (tmp_path / "cv.docx").write_bytes(b"x")
    return tmp_path


def test_sem_word_usa_libreoffice(tmp_path, monkeypatch):
    chamadas = _simular(monkeypatch, word=False, soffice="soffice")
    converter_pdf(_pasta_com_docx(tmp_path))
    assert chamadas[0][:4] == ["soffice", "--headless", "--convert-to", "pdf"]
    assert (tmp_path / "cv.pdf").exists()


def test_word_falha_e_libreoffice_assume(tmp_path, monkeypatch):
    chamadas = _simular(monkeypatch, word=True, soffice="soffice", word_falha=True)
    converter_pdf(_pasta_com_docx(tmp_path))
    assert [c[0] for c in chamadas] == ["powershell", "soffice"]


def test_sem_conversor_explica_o_que_instalar(tmp_path, monkeypatch):
    _simular(monkeypatch, word=False, soffice=None)
    with pytest.raises(RuntimeError, match="LibreOffice"):
        converter_pdf(_pasta_com_docx(tmp_path))
