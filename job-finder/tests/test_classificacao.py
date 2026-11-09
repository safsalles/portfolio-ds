import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import afinidade  # noqa: E402
import classificacao as c  # noqa: E402
import empresas  # noqa: E402
from util import nova_vaga  # noqa: E402

GRANDES = c.carregar_empresas_grandes()


def vaga(titulo, empresa="", local="", modelo="", descricao="", futebol=False):
  return nova_vaga(titulo, empresa, f"https://x/{titulo}", "teste", local=local,
                   modelo=modelo, descricao=descricao, fonte_de_futebol=futebol)


def classificar_uma(v):
  aceitas = c.classificar([v], GRANDES)
  return aceitas[0] if aceitas else None


# --- categorias ---

def test_categorias_pelo_titulo():
  assert c.categoria_geral("Analista de Dados Pleno") == c.DADOS
  assert c.categoria_geral("Data Analyst") == c.DADOS
  assert c.categoria_geral("Analista de BI Sênior") == c.BI
  assert c.categoria_geral("Analista de Business Intelligence") == c.BI
  assert c.categoria_geral("Assistente Administrativo") == c.ADMIN
  assert c.categoria_geral("Administrative Assistant") == c.ADMIN
  assert c.categoria_geral("Engenheiro de Produção") == c.OUTRAS
  assert c.categoria_geral("Analista Jurídico") is None


def test_bi_nao_casa_dentro_de_outra_palavra():
  assert c.categoria_geral("Bibliotecário") is None


def test_titulos_excluidos():
  assert c.titulo_excluido("Estágio em Dados")
  assert c.titulo_excluido("Engenheiro de Dados")
  assert c.titulo_excluido("Data Engineer")
  assert not c.titulo_excluido("International Data Analyst")


# --- vagas gerais ---

def test_vaga_geral_precisa_ser_remota():
  assert classificar_uma(vaga("Analista de Dados", "Acme", modelo="hibrido")) is None
  aceita = classificar_uma(vaga("Analista de Dados", "Acme", modelo="remoto"))
  assert aceita["categoria"] == c.DADOS and aceita["prioridade"] == c.P_OUTRAS


def test_grande_empresa_tem_prioridade_1():
  aceita = classificar_uma(vaga("Analista de BI", "Itaú Unibanco", modelo="remoto"))
  assert aceita["prioridade"] == c.P_GRANDE


def test_grande_empresa_por_palavra_inteira():
  assert c.eh_grande_empresa("Itaú Unibanco", GRANDES)
  assert c.eh_grande_empresa("iFood", GRANDES)
  assert not c.eh_grande_empresa("Itauna Consultoria", GRANDES)
  assert not c.eh_grande_empresa("Skydropx LATAM", GRANDES)


# --- futebol ---

def test_futebol_presencial_no_brasil_cai_fora():
  v = vaga("Estagiário de Análise de Dados", "Federação Paulista de Futebol",
           local="São Paulo, São Paulo, Brazil", modelo="presencial")
  assert classificar_uma(v) is None


def test_futebol_remoto_no_brasil_entra():
  v = vaga("Analista de Dados", "Federação Paulista de Futebol",
           local="São Paulo, São Paulo, Brazil", modelo="remoto")
  aceita = classificar_uma(v)
  assert aceita["categoria"] == c.FUTEBOL
  assert aceita["prioridade"] == c.P_FUTEBOL
  assert aceita["grupo_local"] == c.LOCAL_BRASIL


def test_futebol_remoto_aceitando_latam():
  v = vaga("Football Data Analyst", "Acme Sports", local="Remote", modelo="remoto",
           descricao="We hire anywhere in LATAM.")
  assert classificar_uma(v)["grupo_local"] == c.LOCAL_REMOTO_OK


def test_futebol_remoto_so_para_reino_unido_cai_fora():
  v = vaga("Data Scientist II (Soccer)", "Teamworks", local="United Kingdom",
           modelo="remoto",
           descricao="Applicants must have the right to work in the UK.")
  assert classificar_uma(v) is None


def test_futebol_remoto_sem_pais_vai_para_conferir():
  v = vaga("Video Scout", "Clube X", local="Remote", modelo="remoto",
           descricao="Part-time role reviewing match footage.")
  assert classificar_uma(v)["grupo_local"] == c.LOCAL_CONFERIR


def test_futebol_presencial_fora_do_brasil_cai_fora():
  v = vaga("1st Team Data Scientist", "Manchester City FC",
           local="Manchester, GB", futebol=True)
  assert classificar_uma(v) is None


def test_funcao_que_nao_interessa_em_empresa_de_futebol_nao_e_futebol():
  assert not c.eh_futebol(vaga("Performance Chef", "Manchester City FC", futebol=True))
  assert not c.eh_futebol(vaga("Account Executive", "Hudl", futebol=True))


def test_futebol_americano_nao_conta():
  assert not c.eh_futebol(vaga("Football Data Analyst", "NFL Network"))


def test_clube_sem_ser_de_futebol_nao_conta():
  assert not c.eh_futebol(vaga("Analista de Dados", "Clube Wine"))


def test_remota_numa_cidade_estrangeira_nao_e_aceita_brasil():
  # Vaga local na Bolívia que cita "South America" na descrição.
  v = vaga("Sports Match Reporter / Data Scout", "FeedConstruct",
           local="Cochabamba, Bolivia", modelo="remoto",
           descricao="Cover matches across South America from your city.")
  assert classificar_uma(v)["grupo_local"] == c.LOCAL_CONFERIR


def test_modelo_lido_da_descricao():
  assert c.modelo_pela_descricao("Analista", "", "Modalidade: 100% Presencial") == "presencial"
  assert c.modelo_pela_descricao("Analista", "", "Trabalho remoto, de qualquer lugar") == "remoto"
  # 4 dias no escritório com "remote flex days": não pode sair como remota.
  assert c.modelo_pela_descricao(
      "Analyst", "", "office at least four days a week, remote flex days") != "remoto"
  assert c.modelo_pela_descricao("Analyst", "", "Hybrid working: 2 days at home") == "hibrido"
  assert c.modelo_pela_descricao("Data Analyst - Remote", "", "") == "remoto"
  assert c.modelo_pela_descricao("Analista", "", "Vaga para analista") == ""


def test_auxilio_home_office_nao_torna_a_vaga_remota():
  # Mercado Pago, Osasco: "Auxílio home office: R$ 200" é benefício.
  beneficios = "Vale refeição: R$ 51,00/dia\nAuxílio home office: R$ 200,00\nSeguro de vida"
  assert c.modelo_pela_descricao("Assistente", "Osasco / SP", beneficios) == ""
  assert c.modelo_pela_descricao("Assistente", "", "Trabalho em home office") == "remoto"
  assert c.modelo_pela_descricao("Assistente", "", "Home office allowance: R$ 200") == ""


def test_futebol_sem_modelo_fora_do_brasil_cai_fora():
  # Era o caso do LinkedIn: a busca dizia "remoto" mas a vaga é presencial.
  v = vaga("U15-16 Performance Analyst", "Manchester United",
           local="Manchester, England, United Kingdom",
           descricao="Our football club... football performance... onsite at Carrington")
  assert c.eh_futebol(v)
  assert classificar_uma(v) is None


def test_vaga_geral_fora_do_brasil_cai_fora():
  v = vaga("Data Analyst", "Gotfriends", local="Center District, Israel", modelo="remoto")
  assert classificar_uma(v) is None


def test_titulos_novos_excluidos():
  assert c.titulo_excluido("Engenheiro(a) Sênior de Dados")
  assert c.titulo_excluido("Analytics Engineer Sênior")
  assert c.titulo_excluido("Group Product Manager, Data Platforms")
  assert c.titulo_excluido("Analista de Banco de Dados Sênior")
  assert not c.titulo_excluido("Engenheiro de Produção")


def test_vaga_antiga_cai_fora():
  v = vaga("Analista de BI", "Acme", modelo="remoto")
  v["minutos"] = 400 * 1440
  assert classificar_uma(v) is None


def test_remota_amarrada_a_outro_pais_vai_para_conferir_mesmo_citando_brasil():
  v = vaga("Game Operations Analyst", "Genius Sports", local="Remote - Estonia",
           modelo="remoto", descricao="We have offices in London and Brazil.",
           futebol=True)
  assert classificar_uma(v)["grupo_local"] == c.LOCAL_CONFERIR


def test_operacoes_de_futebol_no_brasil_entram_se_remotas():
  v = vaga("Football Operations Specialist", "Genius Sports",
           local="Rio de Janeiro, Rio de Janeiro, Brazil", modelo="remoto", futebol=True)
  assert classificar_uma(v)["grupo_local"] == c.LOCAL_BRASIL


# --- ordem no e-mail ---

def test_ordem_futebol_grandes_resto():
  vagas = c.classificar([
      vaga("Analista de Dados", "Acme", modelo="remoto"),
      vaga("Analista de BI", "Nubank", modelo="remoto"),
      vaga("Analista de Desempenho", "Esporte Clube Bahia",
           local="Salvador, Brazil", modelo="remoto"),
  ], GRANDES)
  ordem = [v["empresa"] for v in c.ordenar(vagas)]
  assert ordem == ["Esporte Clube Bahia", "Nubank", "Acme"]


# --- sua avaliação das empresas ---

AVALIACOES = {
    "genius sports": {"nome": "Genius Sports", "nota": "quero muito", "descricao": "Dados esportivos"},
    "bairesdev": {"nome": "BairesDev", "nota": "quero", "descricao": "Consultoria remota"},
    "bma advogados": {"nome": "BMA Advogados", "nota": "meh", "descricao": ""},
    "chata": {"nome": "Chata", "nota": "evitar", "descricao": ""},
}


def test_notas_mudam_o_bloco_e_evitar_some():
  vagas = c.classificar([
      vaga("Analista de Dados", "Acme", modelo="remoto"),
      vaga("BI Analyst", "BairesDev", modelo="remoto"),
      vaga("Assistente Administrativo", "BMA Advogados", modelo="remoto"),
      vaga("Analista de Dados", "Chata S.A.", modelo="remoto"),
      vaga("Analista de BI", "Nubank", modelo="remoto"),
  ], GRANDES, AVALIACOES)
  ordem = [(v["empresa"], v["prioridade"]) for v in c.ordenar(vagas)]
  assert ordem == [("BairesDev", c.P_QUERO), ("Nubank", c.P_GRANDE),
                   ("Acme", c.P_OUTRAS), ("BMA Advogados", c.P_MEH)]


def test_avaliacao_por_nome_inteiro():
  assert empresas.avaliacao("Genius Sports Group", AVALIACOES)["nota"] == "quero muito"
  assert empresas.avaliacao("Geniuses Ltd", AVALIACOES) is None


def test_arquivo_de_empresas_le_as_notas():
  avaliacoes = empresas.carregar()
  assert avaliacoes["genius sports"]["nota"] == "quero muito"
  assert all(a["nota"] in empresas.NOTAS for a in avaliacoes.values())


def test_empresas_para_avaliar_so_as_que_faltam():
  vagas = [dict(vaga("x", "Acme"), nota=None, sobre_empresa="Fabricante (Wikipédia)"),
           dict(vaga("y", "BairesDev"), nota="quero", sobre_empresa=""),
           dict(vaga("z", "Acme"), nota=None, sobre_empresa="")]
  assert empresas.empresas_para_avaliar(vagas) == ["Acme | ok | Fabricante"]


# --- afinidade ---

MINHAS = {"SQL", "Python", "Power BI", "Excel"}


def test_afinidade_pelo_que_a_vaga_pede():
  v = vaga("Analista de Dados", descricao="Requisitos: SQL, Python, Power BI e AWS.")
  porcentagem, tenho, faltam = afinidade.calcular(v, MINHAS)
  assert porcentagem == 75 and faltam == ["AWS"]


def test_afinidade_sem_base_fica_vazia():
  assert afinidade.calcular(vaga("Analista de Dados"), MINHAS) is None
  assert afinidade.calcular(vaga("Analista", descricao="Vaga com SQL."), MINHAS) is None


def test_suas_competencias_saem_do_curriculo():
  minhas = afinidade.minhas_competencias()
  assert {"SQL", "Python", "Power BI"} <= minhas
  assert "Spark" not in minhas


def test_empresa_confidencial_cai_fora():
  assert classificar_uma(vaga("Analista de Dados", "Empresa Confidencial", modelo="remoto")) is None


# --- descrição da empresa pela Gupy e pelo LinkedIn ---

def test_sobre_da_gupy():
  html = ('..."about":"\u003cp\u003eO que te encanta? ❤️\u003c/p\u003e\u003cp\u003e❤️ '
          'Muito além da maior varejista de moda do país, somos um ecossistema.\u003c/p\u003e"...')
  assert empresas.ler_sobre_gupy(html) == \
      "Muito além da maior varejista de moda do país, somos um ecossistema."


def test_pagina_da_empresa_no_linkedin():
  html = ('<meta name="description" content="Super Lagoa | 30.057 seguidores no LinkedIn. '
          'Feliz com você todo dia! | O Grupo Lagoa é uma empresa cearense, com 35 anos de '
          'tradição. São 16 lojas.">'
          '<dt>Tamanho da empresa</dt> <dd>1.001-5.000 funcionários</dd>')
  texto, porte = empresas.ler_pagina_linkedin(html)
  assert texto == "O Grupo Lagoa é uma empresa cearense, com 35 anos de tradição."
  assert porte == "1.001-5.000 funcionários"


# --- nível, engenharia de dados, PcD e vagas operacionais em inglês ---

def test_nivel_alto_e_data_science_so_de_abertura():
  for t in ("Senior Data Scientist", "Cientista de Dados Sr", "Data Scientist",
            "Cientista de Dados Pleno", "Machine Learning Engineer", "Data Engineer",
            "Senior Data Engineer", "Engenheiro de Dados"):
    assert c.nivel_nao_serve(t), t
  # Analista de dados e de BI sênior continuam entrando.
  for t in ("Data Scientist I", "Junior Data Scientist", "Cientista de Dados Jr",
            "Analista de Dados Pleno", "Analista de Dados Sênior", "Analista de BI Sênior",
            "Senior Data Analyst", "Lead Data Analyst", "Football Data Analyst"):
    assert not c.nivel_nao_serve(t), t


def test_cientista_e_engenheiro_de_dados_tambem_caem_no_futebol():
  v = vaga("Senior Data Scientist", "Genius Sports", local="Remote", modelo="remoto",
           descricao="Anywhere in LATAM", futebol=True)
  assert classificar_uma(v) is None
  v = vaga("Football Data Engineer", "Genius Sports", local="Remote", modelo="remoto",
           descricao="Anywhere in LATAM", futebol=True)
  assert classificar_uma(v) is None


def test_vaga_exclusiva_para_pcd_ou_minorias_cai_fora():
  assert classificar_uma(vaga("Assistente Administrativo - PCD", "Acme", modelo="remoto")) is None
  assert classificar_uma(vaga("Analista de Dados", "Acme", modelo="remoto",
                              descricao="Vaga exclusiva para pessoas com deficiência.")) is None
  assert classificar_uma(vaga("Analista de Dados", "Acme", modelo="remoto",
                              descricao="Vaga afirmativa para mulheres.")) is None
  # "PcD bem-vindas" não é exclusiva: a vaga fica.
  assert classificar_uma(vaga("Analista de Dados", "Acme", modelo="remoto",
                              descricao="Pessoas com deficiência são bem-vindas.")) is not None


def test_funcoes_operacionais_em_ingles():
  for t in ("Data Entry Clerk", "Data Operator", "Administrative Assistant",
            "Administrative Analyst", "Data Entry Specialist"):
    assert c.categoria_geral(t) == c.ADMIN, t
  aceita = classificar_uma(vaga("Administrative Assistant", "Acme", local="Latin America",
                                modelo="remoto"))
  assert aceita["categoria"] == c.ADMIN


def test_vaga_geral_em_ingles_restrita_a_um_pais_cai_fora():
  v = vaga("Data Entry Specialist", "Acme", local="Remote", modelo="remoto",
           descricao="Candidates must be based in the US and authorized to work in the US.")
  assert classificar_uma(v) is None


def test_bolsa_do_iel_com_sql_python_entra_e_doutor_nao():
  import classificacao as c
  for titulo in ("Bolsista Mestre [SQL, Modelagem Relacional, Data Quality, Python/Pyspark] ICT",
                 "Bolsista Mestre [Dados Em CRM, SQL, Python ] Bradesco",
                 "Bolsista Mestre ( Cientista De Dados – NLP E Sistemas De Busca)"):
    assert c.categoria_geral(titulo) == c.DADOS
    assert not c.titulo_excluido(titulo)
    assert not c.nivel_nao_serve(titulo)  # bolsa é nível de abertura
  assert c.titulo_excluido("Bolsista Doutor [Garantias, Agente Inteligente, IA Generativa]")
  assert c.nivel_nao_serve("Senior Data Scientist")  # sem bolsa, continua cortando


def test_bolsa_aceita_mais_dias_que_vaga_comum():
  bolsa = nova_vaga("Bolsista Mestre [SQL, Python]", "IEL", "https://x/b", "InfoJobs",
                    local="Todo Brasil", minutos=77 * 1440)
  comum = nova_vaga("Analista de Dados", "Acme", "https://x/c", "InfoJobs",
                    local="Brasil", minutos=77 * 1440)
  assert not c.antiga(bolsa)
  assert c.antiga(comum)
  assert c.antiga(dict(bolsa, minutos=130 * 1440))
