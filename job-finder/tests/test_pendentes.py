import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pendentes  # noqa: E402


def test_guarda_e_le_as_vagas(tmp_path):
  vagas = [{"titulo": "Analista de Dados", "empresa": "Acme", "link": "https://x/1", "nova": True}]
  pendentes.salvar("radar", vagas, pasta=str(tmp_path))
  assert pendentes.carregar("radar", pasta=str(tmp_path)) == vagas


def test_sem_arquivo_devolve_none(tmp_path):
  assert pendentes.carregar("perto", pasta=str(tmp_path)) is None


def test_apagar_remove_o_arquivo(tmp_path):
  pendentes.salvar("radar", [], pasta=str(tmp_path))
  pendentes.apagar("radar", pasta=str(tmp_path))
  assert pendentes.carregar("radar", pasta=str(tmp_path)) is None
