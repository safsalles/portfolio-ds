import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import perto_de_casa as p  # noqa: E402
from util import nova_vaga  # noqa: E402

FILTROS = p.carregar_filtros()


def vaga(titulo, empresa="Acme", local="Macaé, Rio de Janeiro, Brasil", modelo="presencial"):
  return nova_vaga(titulo, empresa, f"https://x/{titulo}/{local}", "teste",
                   local=local, modelo=modelo)


def test_cargos_ruins_e_profissoes_que_voce_nao_tem_saem():
  for titulo in ("Estoquista", "Repositor de Mercadorias", "Médico do Trabalho",
                 "Farmacêutico Responsável", "Dentista", "Operador de Empilhadeira",
                 "Auxiliar de Serviços Gerais", "Enfermeira", "Professor de Matemática",
                 "Estágio em Administração", "LAVADOR DE VEÍCULOS - GW LIDER - MACAÉ/RJ",
                 "AUX. DE OPERACOES | MACAÉ/RJ", "Analista De Engenharia Mecânica"):
    assert not p.titulo_serve(titulo, FILTROS), titulo


def test_loja_vendas_fiscal_ti_e_ambiente_saem():
  for titulo in ("Líder De Loja | ATACADÃO", "COORDENADOR DE LOJA - Campos", "Gerente de Loja",
                 "Operador de Loja", "ANALISTA DE POS VENDAS", "GERENTE DE VENDAS - SGA TOYOTA",
                 "Analista Comercial De Vendas", "Analista Fiscal Sênior", "Analista Contábil Pleno",
                 "Analista De TI", "Analista de Sistemas", "Analista de Suporte PL",
                 "Analista de Meio Ambiente", "Analista de Relacionamento Comercial"):
    assert not p.titulo_serve(titulo, FILTROS), titulo


def test_empresas_que_voce_quer_evitar():
  import empresas
  avaliacoes = empresas.carregar()
  for empresa in ("Barcelos", "ATACADAO", "Assaí Atacadista", "DOME Serviços Integrados",
                  "Lojas Renner"):
    assert empresas.avaliacao(empresa, avaliacoes)["nota"] == "evitar", empresa


def test_cargos_do_seu_perfil_entram():
  for titulo in ("Analista Administrativo", "Assistente Administrativo",
                 "Analista de Planejamento", "Comprador Pleno", "Analista de BI",
                 "Coordenador de Logística", "Analista de Fluxo de Caixa",
                 "Analista de Medição", "Supervisor de Qualidade"):
    assert p.titulo_serve(titulo, FILTROS), titulo


def test_professor_so_de_faculdade():
  assert p.titulo_serve("Professor de Administração - Ensino Superior", FILTROS)
  assert p.titulo_serve("Docente de Graduação em Engenharia de Produção", FILTROS)
  assert p.titulo_serve("Professor Universitário - Estatística", FILTROS)
  assert not p.titulo_serve("Professor de Matemática - Ensino Fundamental", FILTROS)
  assert not p.titulo_serve("Professor de Inglês", FILTROS)


def test_bi_so_como_palavra_inteira():
  assert not p.titulo_serve("Recepcionista Bilíngue", FILTROS)
  assert not p.titulo_serve("Tradutor Bilíngue", FILTROS)


def test_cidade_lida_de_formatos_diferentes():
  assert p.cidade_da_vaga(vaga("x", local="Macaé - RJ, Brasil")) == "Macaé"
  assert p.cidade_da_vaga(vaga("x", local="Campos dos Goytacazes, Rio de Janeiro, Brasil")) \
      == "Campos dos Goytacazes"
  assert p.cidade_da_vaga(vaga("x", local="Campos Goytacazes - RJ, Brasil")) == "Campos dos Goytacazes"
  assert p.cidade_da_vaga(vaga("x", local="São João da Barra / RJ, Brasil")) == "São João da Barra"
  assert p.cidade_da_vaga(vaga("x", local="Rio de Janeiro, Brasil")) is None


def test_filtro_tira_remota_fora_das_cidades_e_repetida_e_ordena_por_empresa():
  aceitas = p.filtrar([
      vaga("Analista Administrativo", "Zeta"),
      vaga("Analista Administrativo", "Zeta"),  # a mesma vaga em outra fonte
      vaga("Analista de Compras", "Alfa", modelo="hibrido"),
      vaga("Analista de Dados", "Beta", modelo="remoto"),
      vaga("Analista de Compras", "Gama", local="Niterói, Rio de Janeiro, Brasil"),
      vaga("Analista Financeiro", "Empresa Confidencial"),
      vaga("Estoquista", "Alfa"),
  ], FILTROS, {})
  assert [v["empresa"] for v in aceitas] == ["Alfa", "Zeta"]
  assert aceitas[0]["cidade"] == "Macaé"
