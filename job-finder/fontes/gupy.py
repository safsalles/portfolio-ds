"""Gupy: busca do portal de vagas (portal.gupy.io), que tem uma API pública."""

from urllib.parse import quote

from util import baixar_json, limpar_html, minutos_desde, nova_vaga

URL = "https://portal.gupy.io/api/job-search/jobs?jobName={termo}&limit=100&offset=0"

MODELOS = {"remote": "remoto", "hybrid": "hibrido", "on-site": "presencial"}


def buscar(termos):
  vagas = {}
  for termo in termos:
    dados = baixar_json(URL.format(termo=quote(termo)))
    if not dados:
      continue
    lista = dados.get("data") or []
    print(f"   Gupy: '{termo}' -> {len(lista)} vagas")
    for j in lista:
      link = (j.get("jobUrl") or "").split("?")[0]
      if not link or link in vagas:
        continue
      minutos, rotulo = minutos_desde(j.get("publishedDate"))
      cidade = ", ".join(x for x in (j.get("city"), j.get("state")) if x)
      vagas[link] = nova_vaga(
          j.get("name"), j.get("careerPageName"), link, "Gupy",
          local=f"{cidade}, Brasil" if cidade else "Brasil",
          modelo=MODELOS.get(j.get("workplaceType"), ""),
          minutos=minutos, publicada=rotulo,
          descricao=limpar_html(j.get("description"))[:3000],
      )
  return list(vagas.values())
