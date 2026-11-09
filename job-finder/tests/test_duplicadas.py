import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memoria  # noqa: E402
import perto_de_casa as p  # noqa: E402
from util import empresa_base, nova_vaga  # noqa: E402


def vaga(titulo, empresa, fonte, local="Remoto"):
  return nova_vaga(titulo, empresa, f"https://{fonte}/{titulo}", fonte, local=local)


def test_empresa_base_ignora_sufixos():
  assert empresa_base("Vetta Tecnologia") == empresa_base("Vetta") == "vetta"
  assert empresa_base("Grupo SysMap") == empresa_base("SysMap")
  assert empresa_base("Acme Ltda.") == empresa_base("ACME S.A.") == "acme"
  assert empresa_base("Tecnologia") == "tecnologia"  # nunca fica vazio
  assert empresa_base("Magalu") != empresa_base("Magazine Luiza")


def test_mesma_vaga_em_duas_fontes_com_nome_de_empresa_diferente_sai_uma_vez():
  a = vaga("Analista de BI Pleno", "Vetta Tecnologia", "gupy")
  b = vaga("Analista de BI Pleno", "Vetta", "linkedin")
  c = vaga("Analista de BI Pleno", "Outra Empresa", "linkedin")
  assert memoria.filtrar_novas([a, b, c], {}) == [a, c]


def test_memoria_antiga_continua_valendo():
  antiga = {"analista de bi pleno|vetta": "2026-11-01"}
  assert memoria.filtrar_novas([vaga("Analista de BI Pleno", "Vetta", "x")], antiga) == []


def test_perto_de_casa_tambem_junta_repetidas():
  filtros = p.carregar_filtros()
  a = vaga("Analista Administrativo", "Acme Ltda", "gupy", "Macaé, Rio de Janeiro, Brasil")
  b = vaga("Analista Administrativo", "Acme", "linkedin", "Macaé, Rio de Janeiro, Brazil")
  a["modelo"] = b["modelo"] = "presencial"
  assert len(p.filtrar([a, b], filtros, {})) == 1
