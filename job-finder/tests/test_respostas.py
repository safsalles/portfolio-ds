import os
import sys
from datetime import date
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import email_vagas  # noqa: E402
import empresas  # noqa: E402
import respostas as r  # noqa: E402
from util import nova_vaga  # noqa: E402

HOJE = date(2026, 11, 8)


def vaga(titulo="Analista de Dados", empresa="Acme"):
  return nova_vaga(titulo, empresa, f"https://x/{titulo}", "teste", local="Remoto")


def test_codigo_igual_para_a_mesma_vaga_em_fontes_diferentes():
  a, b = vaga(), vaga()
  b["link"] = "https://outra-fonte/123"
  assert r.codigo(a) == r.codigo(b)
  assert r.codigo(a) != r.codigo(vaga("Analista de BI"))
  assert len(r.codigo(a)) == 8


def test_link_de_resposta_vira_assunto_que_o_bot_entende():
  v = vaga("Analista de Dados Pleno", "Ação & Cia")
  link = r.link_resposta(r.CANDIDATEI, v, "bot@gmail.com")
  assert link.startswith("mailto:bot@gmail.com?subject=")
  assunto = unquote(link.split("subject=")[1].split("&")[0])
  assert assunto == f"Radar: candidatei #{r.codigo(v)} (Analista de Dados Pleno | Ação & Cia)"
  assert r.ler_assunto(assunto) == (r.CANDIDATEI, r.codigo(v), "Analista de Dados Pleno | Ação & Cia")


def test_ler_assunto_aceita_re_e_ignora_outros_emails():
  assert r.ler_assunto("Re: Radar: descartar #0123abcd (X | Y)")[:2] == (r.DESCARTAR, "0123abcd")
  assert r.ler_assunto("RES: Radar: Nunca mais #0123abcd (Acme)")[0] == r.NUNCA_MAIS
  assert r.ler_assunto("Radar de Vagas: 40 vaga(s) aberta(s)") is None
  assert r.ler_assunto("Radar: candidatei sem código") is None


def test_candidatei_e_descartar_tiram_a_vaga_e_candidatadas_aparecem_na_secao():
  estado = r.vazio()
  a, b, c = vaga("A"), vaga("B"), vaga("C")
  r.lembrar(estado, [a, b, c], "radar", hoje=HOJE)
  r.aplicar(estado, r.CANDIDATEI, r.codigo(a), data="2026-11-05")
  r.aplicar(estado, r.DESCARTAR, r.codigo(b), data="2026-11-06")
  assert r.tirar_marcadas([a, b, c], estado) == [c]
  feitas = r.candidatadas(estado, "radar", hoje=HOJE)
  assert [v["titulo"] for v in feitas] == ["A"]
  assert r.candidatadas(estado, "perto", hoje=HOJE) == []
  # Depois de 30 dias, sai da seção (mas a vaga continua fora da lista).
  assert r.candidatadas(estado, "radar", hoje=date(2026, 12, 20)) == []


def test_resposta_lida_de_novo_mantem_a_data_original():
  estado = r.vazio()
  a = vaga()
  r.lembrar(estado, [a], "radar", hoje=HOJE)
  r.aplicar(estado, r.CANDIDATEI, r.codigo(a), data="2026-11-01")
  r.aplicar(estado, r.CANDIDATEI, r.codigo(a), data="2026-11-08")
  assert estado["vagas"][r.codigo(a)]["data"] == "2026-11-01"


def test_vaga_fora_do_indice_usa_o_texto_do_assunto():
  estado = r.vazio()
  r.aplicar(estado, r.CANDIDATEI, "deadbeef", "Analista de BI | Acme", data="2026-11-08")
  assert estado["vagas"]["deadbeef"]["empresa"] == "Acme"


def test_nunca_mais_vira_evitar():
  estado = r.vazio()
  a = vaga(empresa="Empresa Chata")
  r.lembrar(estado, [a], "perto", hoje=HOJE)
  r.aplicar(estado, r.NUNCA_MAIS, r.codigo(a))
  r.aplicar(estado, r.NUNCA_MAIS, "deadbeef", "Outra Ltda")
  avaliacoes = {"outra ltda": {"nome": "Outra Ltda", "nota": empresas.QUERO, "descricao": ""}}
  r.evitar_empresas(estado, avaliacoes)
  assert empresas.avaliacao("Empresa Chata", avaliacoes)["nota"] == empresas.EVITAR
  assert avaliacoes["outra ltda"]["nota"] == empresas.EVITAR


def test_email_tem_os_links_e_a_secao_ja_me_candidatei():
  v = vaga()
  v.update(prioridade=3, categoria="Análise de Dados", grupo_local="Brasil", publicada="hoje")
  ja = [{"titulo": "Analista X", "empresa": "Beta", "link": "https://b", "data": "2026-11-05"}]
  html = email_vagas.montar_html([v], "oi", None, "bot@gmail.com", ja)
  assert "Já me candidatei</a>" in html and "Nunca mais essa empresa" in html
  assert "✅ Já me candidatei (1)" in html and "05/11" in html
  # Sem remetente (prévia sem config), sem links.
  assert "mailto:" not in email_vagas.montar_html([v], "oi")
