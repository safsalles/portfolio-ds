"""Empresas de dados de futebol, lidas direto dos sistemas de vagas delas.

Esses sistemas (Greenhouse, Lever, SmartRecruiters) têm APIs públicas que
só listam vagas abertas. Para incluir outra empresa, ache o nome dela na URL
da página de vagas (ex.: job-boards.greenhouse.io/hudl -> "hudl") e adicione
na lista certa abaixo.
"""

from classificacao import PADRAO_FUNCAO_FUTEBOL
from util import baixar_json, limpar_html, minutos_desde, normalizar, nova_vaga

GREENHOUSE = {"hudl": "Hudl", "geniussports": "Genius Sports"}
LEVER = {"kitmanlabs": "Kitman Labs"}
SMARTRECRUITERS = {"Sportradar": "Sportradar"}


def _modelo(local, remoto=False):
  return "remoto" if remoto or "remote" in normalizar(local) else ""


def _greenhouse():
  vagas = []
  for codigo, nome in GREENHOUSE.items():
    dados = baixar_json(
        f"https://boards-api.greenhouse.io/v1/boards/{codigo}/jobs?content=true"
    )
    lista = (dados or {}).get("jobs", [])
    print(f"   {nome} (Greenhouse): {len(lista)} vagas abertas")
    for j in lista:
      local = (j.get("location") or {}).get("name", "")
      minutos, rotulo = minutos_desde(j.get("first_published") or j.get("updated_at"))
      vagas.append(nova_vaga(
          j.get("title"), nome, j.get("absolute_url"), nome,
          local=local, modelo=_modelo(local), minutos=minutos, publicada=rotulo,
          descricao=limpar_html(j.get("content")), fonte_de_futebol=True,
      ))
  return vagas


def _lever():
  vagas = []
  for codigo, nome in LEVER.items():
    lista = baixar_json(f"https://api.lever.co/v0/postings/{codigo}?mode=json") or []
    print(f"   {nome} (Lever): {len(lista)} vagas abertas")
    for j in lista:
      categorias = j.get("categories") or {}
      local = categorias.get("location") or ""
      remoto = normalizar(j.get("workplaceType") or "") == "remote"
      minutos, rotulo = minutos_desde(j.get("createdAt"))
      vagas.append(nova_vaga(
          j.get("text"), nome, j.get("hostedUrl"), nome,
          local=local, modelo=_modelo(local, remoto), minutos=minutos,
          publicada=rotulo,
          descricao=limpar_html(j.get("descriptionPlain") or j.get("description")),
          fonte_de_futebol=True,
      ))
  return vagas


def _smartrecruiters():
  vagas = []
  base = "https://api.smartrecruiters.com/v1/companies/{c}/postings"
  for codigo, nome in SMARTRECRUITERS.items():
    lista = (baixar_json(base.format(c=codigo) + "?limit=100") or {}).get("content", [])
    print(f"   {nome} (SmartRecruiters): {len(lista)} vagas abertas")
    for j in lista:
      titulo = j.get("name", "")
      loc = j.get("location") or {}
      local = ", ".join(x for x in (loc.get("city"), (loc.get("country") or "").upper()) if x)
      if (loc.get("country") or "").lower() == "br":
        local += " (Brazil)"
      descricao = ""
      # A lista não traz a descrição; só abrimos as vagas de funções que
      # interessam, pra não fazer 80 pedidos à toa.
      if PADRAO_FUNCAO_FUTEBOL.search(normalizar(titulo)):
        detalhe = baixar_json(base.format(c=codigo) + f"/{j.get('id')}") or {}
        secoes = ((detalhe.get("jobAd") or {}).get("sections") or {}).values()
        descricao = limpar_html(" ".join(s.get("text", "") for s in secoes))
      minutos, rotulo = minutos_desde(j.get("releasedDate"))
      vagas.append(nova_vaga(
          titulo, nome, f"https://jobs.smartrecruiters.com/{codigo}/{j.get('id')}",
          nome, local=local, modelo=_modelo(local, loc.get("remote")),
          minutos=minutos, publicada=rotulo, descricao=descricao,
          fonte_de_futebol=True,
      ))
  return vagas


def buscar():
  return _greenhouse() + _lever() + _smartrecruiters()
