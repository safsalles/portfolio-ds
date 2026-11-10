import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fontes import solides  # noqa: E402

LISTA = (
    '{\\"data\\":[{\\"killerQuestions\\":[],\\"id\\":950376,'
    '\\"title\\":\\"Analista de Dados \u0026 BI\\",\\"description\\":\\"$1e\\",'
    '\\"companyName\\":\\"BEE TECNOLOGIA LTDA\\",\\"jobType\\":\\"remoto\\",'
    '\\"createdAt\\":\\"2026-11-08\\"},'
    '{\\"killerQuestions\\":[],\\"id\\":950377,\\"title\\":\\"Gerente\\",'
    '\\"description\\":\\"$1f\\",\\"companyName\\":\\"ACME\\",\\"jobType\\":\\"hibrido\\",'
    '\\"createdAt\\":\\"2026-11-01\\"}]}'
)


def test_vagas_da_lista_le_titulo_empresa_data_e_tipo():
  achadas = solides.vagas_da_lista(LISTA)
  assert achadas[0] == ("950376", "Analista de Dados & BI", "BEE TECNOLOGIA LTDA",
                        "2026-11-08", "remoto")
  assert achadas[1][0] == "950377" and achadas[1][4] == "hibrido"


def test_pagina_vazia_nao_quebra():
  assert solides.vagas_da_lista("") == []
  assert solides.vagas_da_lista("<html></html>") == []


def test_converter_monta_o_link_e_o_modelo():
  v = solides.converter("950376", "Analista", "ACME", "2026-11-08", "remoto")
  assert v["link"] == "https://vagas.solides.com.br/vaga/950376"
  assert v["modelo"] == "remoto" and v["fonte"] == "Sólides"
  assert solides.converter("1", "X", "Y", "", "hibrido")["modelo"] == ""
