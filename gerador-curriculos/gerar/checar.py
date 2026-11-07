"""Confere os PDFs gerados: número de páginas e números presentes na base."""
import re
from pathlib import Path

from pypdf import PdfReader

MAX_PAGINAS = 2
NUMERO = re.compile(r"\d+(?:[.,]\d+)*")
MILHAR = re.compile(r"\d{1,3}(?:[.,]\d{3})+")
NAO_CONFIRMADOS = {"pendencias", "credencial"}


def _normalizar(numero: str) -> str:
    if MILHAR.fullmatch(numero):
        return numero.replace(".", "").replace(",", "")
    return numero.replace(",", ".")


def _textos(valor) -> list[str]:
    if isinstance(valor, dict):
        return [t for k, v in valor.items() if k not in NAO_CONFIRMADOS for t in _textos(v)]
    if isinstance(valor, list):
        return [t for v in valor for t in _textos(v)]
    return [] if valor is None else [str(valor)]


def numeros_fora_da_base(texto: str, base: dict) -> list[str]:
    conhecidos = {_normalizar(n) for t in _textos(base) for n in NUMERO.findall(t)}
    return [n for n in dict.fromkeys(NUMERO.findall(texto)) if _normalizar(n) not in conhecidos]


def checar_pdf(pdf: Path, base: dict) -> list[str]:
    leitor = PdfReader(str(pdf))
    erros = []
    if len(leitor.pages) > MAX_PAGINAS:
        erros.append(f"{pdf.name}: {len(leitor.pages)} páginas, o máximo é {MAX_PAGINAS}.")
    texto = "\n".join(p.extract_text() or "" for p in leitor.pages)
    for numero in numeros_fora_da_base(texto, base):
        erros.append(f"{pdf.name}: o número {numero} não existe na base.")
    return erros
