"""Gera os currículos em PDF. Uso: py gerar\\gerar.py [--vaga nome]"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arquivar import publicar  # noqa: E402
from base import IDIOMAS, carregar_base, carregar_versao, carregar_versoes, validar  # noqa: E402
from checar import checar_pdf  # noqa: E402
from documento import montar_docx  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT_PDF = Path(__file__).resolve().parent / "para_pdf.ps1"


LIBREOFFICE_WINDOWS = [Path(os.environ.get(v, "")) / "LibreOffice" / "program" / "soffice.exe"
                       for v in ("ProgramFiles", "ProgramFiles(x86)")]


def _tem_word() -> bool:
    return sys.platform == "win32" and shutil.which("powershell") is not None


def _achar_libreoffice() -> str | None:
    achado = shutil.which("soffice") or shutil.which("libreoffice")
    if achado:
        return achado
    return next((str(p) for p in LIBREOFFICE_WINDOWS if p.is_file()), None)


def _rodar(comando: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(comando, capture_output=True, text=True, errors="replace")


def converter_pdf(pasta: Path) -> None:
    """Converte os .docx da pasta em PDF: pelo Word no Windows, senão pelo LibreOffice."""
    problemas = []
    if _tem_word():
        resultado = _rodar(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                            "-File", str(SCRIPT_PDF), "-Pasta", str(pasta)])
        if resultado.returncode == 0:
            return
        problemas.append(f"Word: {resultado.stderr.strip()}")
    soffice = _achar_libreoffice()
    if soffice is None:
        problemas.append("LibreOffice não encontrado; instale-o ou use o Microsoft Word no Windows")
    else:
        documentos = sorted(pasta.glob("*.docx"))
        resultado = _rodar([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pasta),
                            *map(str, documentos)])
        if resultado.returncode == 0 and all(d.with_suffix(".pdf").exists() for d in documentos):
            return
        problemas.append(f"LibreOffice: {resultado.stderr.strip()}")
    raise RuntimeError("Falha ao converter para PDF. " + " | ".join(problemas))


def _nome(versao_id: str, idioma: str) -> str:
    return f"Sergio_Salles_{versao_id.capitalize()}_{idioma.upper()}"


def _carregar_vaga(raiz: Path, nome: str) -> dict:
    vaga = carregar_versao(raiz / "versoes" / "vagas" / f"{nome}.yaml")
    pai = carregar_versao(raiz / "versoes" / f"{vaga['herda']}.yaml")
    trocas = {k: v for k, v in vaga.items() if v not in ({}, [], None) and k != "herda"}
    return {**pai, **trocas, "id": nome}


def _gerar_em(pasta: Path, base: dict, versoes: list[dict]) -> list[str]:
    for versao in versoes:
        for idioma in versao.get("idiomas", IDIOMAS):
            montar_docx(base, versao, idioma, pasta / f"{_nome(versao['id'], idioma)}.docx")
    converter_pdf(pasta)
    return [e for pdf in sorted(pasta.glob("*.pdf")) for e in checar_pdf(pdf, base)]


def main(raiz: Path = RAIZ, vaga: str | None = None) -> int:
    try:
        base = carregar_base(raiz / "base")
        if vaga:
            versoes = [_carregar_vaga(raiz, vaga)]
        else:
            versoes = carregar_versoes(raiz / "versoes")
    except (ValueError, OSError) as erro:
        print(erro)
        return 1

    erros = validar(base, versoes)
    if erros:
        print("\n".join(erros))
        return 1

    saida = raiz / "saida" / "vagas" if vaga else raiz / "saida"
    saida.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporaria:
        pasta = Path(temporaria)
        try:
            erros = _gerar_em(pasta, base, versoes)
        except RuntimeError as erro:
            print(erro)
            return 1
        if erros:
            print("\n".join(erros))
            print("Nada foi alterado em saida.")
            return 1
        try:
            if vaga:
                for pdf in pasta.glob("*.pdf"):
                    shutil.copy2(pdf, saida / pdf.name)
            else:
                publicar(pasta, saida, raiz / "historico", datetime.now())
        except OSError as erro:
            print(f"{erro}\nOs PDFs anteriores foram mantidos em saida.")
            return 1
    print(f"Pronto: {saida}")
    return 0


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--vaga")
    sys.exit(main(vaga=argumentos.parse_args().vaga))
