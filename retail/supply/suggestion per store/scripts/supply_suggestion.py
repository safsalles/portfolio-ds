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