# processador_itau_streamlit.py

# Importando bibliotecas necessárias
import pandas as pd
import streamlit as st

# Função para pré-visualização dos arquivos
def preview_file(file):
    df = pd.read_csv(file)
    st.write("Pré-visualização dos dados:")
    st.dataframe(df)

# Função para validação das colunas
def validate_columns(df):
    required_columns = ['coluna1', 'coluna2', 'coluna3']  # Exemplo de colunas necessárias
    for column in required_columns:
        if column not in df.columns:
            st.error(f"A coluna {column} é obrigatória!")
            return False
    return True

# Função para diagnóstico dos dados
def data_diagnosis(df):
    st.write("Diagnóstico dos dados:")
    st.write(df.describe())

# Função para exportação correta dos dados
def export_data(df):
    df.to_csv('dados_exportados.csv', index=False)
    st.success("Dados exportados com sucesso!")

# Interface do Streamlit
st.title("Processador Itaú - Streamlit")
file = st.file_uploader("Faça upload do arquivo CSV", type=['csv'])

if file is not None:
    preview_file(file)
    df = pd.read_csv(file)
    if validate_columns(df):
        data_diagnosis(df)
        export_data(df)