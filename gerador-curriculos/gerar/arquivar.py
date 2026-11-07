"""Guarda os PDFs atuais e coloca os novos, sem deixar a saída pela metade."""
import os
import shutil
from datetime import datetime
from pathlib import Path


def _limpar(destino: Path, historico: Path) -> None:
    destino.rmdir()
    try:
        historico.rmdir()
    except OSError:
        pass


def _devolver(destino: Path, saida: Path, historico: Path) -> None:
    for arquivo in destino.iterdir():
        os.replace(arquivo, saida / arquivo.name)
    _limpar(destino, historico)


def arquivar(saida: Path, historico: Path, agora: datetime) -> Path | None:
    pdfs = sorted(saida.glob("*.pdf"))
    if not pdfs:
        return None
    destino = historico / agora.strftime("%Y-%m-%d_%H%M%S")
    destino.mkdir(parents=True)
    for pdf in pdfs:
        try:
            os.replace(pdf, destino / pdf.name)
        except PermissionError as erro:
            _devolver(destino, saida, historico)
            raise PermissionError(f"Feche o arquivo {pdf.name} e rode de novo.") from erro
    return destino


def publicar(novos: Path, saida: Path, historico: Path, agora: datetime) -> None:
    destino = arquivar(saida, historico, agora)
    pdfs = sorted(novos.glob("*.pdf"))
    try:
        for pdf in pdfs:
            shutil.copy2(pdf, saida / pdf.name)
    except OSError:
        for pdf in pdfs:
            (saida / pdf.name).unlink(missing_ok=True)
        if destino:
            _devolver(destino, saida, historico)
        raise
