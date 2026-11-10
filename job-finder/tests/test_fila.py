import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fila  # noqa: E402


def vaga(**kw):
  base = {"titulo": "Analista de Dados", "empresa": "Acme", "link": "https://x/1",
          "descricao": "Vaga para analista com SQL e Power Bi.", "categoria": "Análise de Dados",
          "modelo": "remoto"}
  return {**base, **kw}


def test_vaga_comum_vai_para_auto():
  assert fila.grupo(vaga(), {}) == ("auto", "")


def test_empresa_quero_vai_para_voce():
  g, _ = fila.grupo(vaga(), {"acme": {"nota": "quero muito"}})
  assert g == "voce"


def test_nota_ok_continua_auto():
  assert fila.grupo(vaga(), {"acme": {"nota": "ok"}})[0] == "auto"


def test_cpf_e_futebol_vao_para_voce():
  assert fila.grupo(vaga(descricao="Informe seu CPF"), {})[0] == "voce"
  assert fila.grupo(vaga(categoria=fila.FUTEBOL), {})[0] == "voce"


def test_modelo_nao_confirmado_vai_para_voce():
  assert fila.grupo(vaga(modelo=""), {})[0] == "voce"
  assert fila.grupo(vaga(modelo="presencial"), {})[0] == "voce"


def test_titulo_de_marketing_e_excluido():
  import classificacao
  assert classificacao.titulo_excluido("Analista de Performance e Growth | Remoto")


def test_curriculo_segue_area_e_idioma():
  assert fila.curriculo(vaga()) == "Sergio_Salles_Dados_PT.pdf"
  en = vaga(descricao="We are looking for an analyst with experience and the team you will join")
  assert fila.curriculo(en) == "Sergio_Salles_Dados_EN.pdf"


def test_montar_pula_vagas_com_resposta():
  estado = {"vagas": {"a1": {}}, "notas_empresas": {}}
  novas = fila.montar([vaga(), vaga(link="https://x/2")], estado,
                      lambda v: "a1" if v["link"].endswith("1") else "b2")
  assert [e["codigo"] for e in novas] == ["b2"]
