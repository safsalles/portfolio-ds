import pandas as pd

# 1. Carregando os dados do SampleSuperstore.csv
# Como o arquivo CSV está na pasta 'data' e o script está na pasta 'scripts', 
# precisamos voltar uma pasta (com '..') para achar o arquivo.
print("Carregando os dados de supply...")
df = pd.read_csv("../data/SampleSuperstore.csv")

# Exibindo as primeiras linhas para confirmar que os dados subiram
print(f"Total de linhas carregadas: {len(df)}")
print("\nPrimeiras linhas da base:")
print(df.head(3))

# 2. Resumo rápido de vendas e lucro por Categoria
print("\n--- Desempenho por Categoria ---")
resumo = df.groupby('Category')[['Sales', 'Profit', 'Quantity']].sum().reset_index()
print(resumo)

# 3. Calculando a Curva ABC por Segmento e CEP (Postal Code)
print("\n--- Processando Curva ABC por Segmento e Localidade (Postal Code) ---")

# Agrupando as vendas por Segmento, CEP e Sub-categoria
abc_base = df.groupby(['Segment', 'Postal Code', 'Sub-Category'])['Sales'].sum().reset_index()

# Ordenando do maior para o menor valor de vendas dentro de cada Segmento e CEP
abc_base = abc_base.sort_values(by=['Segment', 'Postal Code', 'Sales'], ascending=[True, True, False])

# Calculando o acumulado e a porcentagem para definir as Classes (A, B, C)
abc_base['Cumulative Sales'] = abc_base.groupby(['Segment', 'Postal Code'])['Sales'].cumsum()
abc_base['Total Segment/CEP Sales'] = abc_base.groupby(['Segment', 'Postal Code'])['Sales'].transform('sum')
abc_base['Cumulative Percentage'] = (abc_base['Cumulative Sales'] / abc_base['Total Segment/CEP Sales']) * 100

def classify_abc(row):
    if row['Cumulative Percentage'] <= 80:
        return 'A'
    elif row['Cumulative Percentage'] <= 95:
        return 'B'
    else:
        return 'C'

abc_base['ABC Class'] = abc_base.apply(classify_abc, axis=1)

# Exibindo uma amostra do resultado da Curva ABC
print("\nAmostra do resultado da Curva ABC gerada:")
print(abc_base.head(10))