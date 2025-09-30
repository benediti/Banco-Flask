import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io  # Adicionado para manipular arquivos em memória

def normalizar_cpf(cpf):
    """
    Normaliza CPF removendo caracteres não numéricos e garantindo 11 dígitos
    """
    if pd.isna(cpf):
        return None
    import re
    cpf_str = str(cpf)
    cpf_str = re.sub(r'[^\\d]', '', cpf_str)
    if len(cpf_str) > 0 and len(cpf_str) <= 11:
        cpf_str = cpf_str.zfill(11)
    return cpf_str if len(cpf_str) == 11 else None

st.title("Processador de Pagamentos Itaú")
st.write("Selecione os arquivos e processe os pagamentos conforme layout do Itaú.")

base_fixa_file = st.file_uploader("Base de Funcionários (Fixa)", type=["xls", "xlsx"])
pagamentos_file = st.file_uploader("Arquivo de Pagamentos", type=["xlsx"])

if base_fixa_file is not None and pagamentos_file is not None:
    try:
        base_fixa = pd.read_excel(base_fixa_file, header=None, dtype=str)
        pag = pd.read_excel(pagamentos_file, dtype={'CPF/CNPJ': str})
        pag = pag.rename(columns={'CPF/CNPJ': 'cpf', 'Valor categoria/centro de custo': 'valor'})
        pag['cpf_original'] = pag['cpf'].copy()
        pag['cpf'] = pag['cpf'].apply(normalizar_cpf)
        base_fixa['cpf_original'] = base_fixa[4].copy()
        base_fixa[4] = base_fixa[4].apply(normalizar_cpf)
        pag = pag[pag['cpf'].notna()]
        base_fixa = base_fixa[base_fixa[4].notna()]
        cpfs_base = set(base_fixa[4])
        cpfs_pag = set(pag['cpf'])
        cpfs_nao_encontrados = cpfs_pag - cpfs_base
        st.write(f"Pagamentos: {len(pag)} registros válidos")
        st.write(f"Base: {len(base_fixa)} registros válidos")
        st.write(f"CPFs NÃO encontrados na base: {len(cpfs_nao_encontrados)}")
        if cpfs_nao_encontrados:
            lista_nao_encontrados = pag[pag['cpf'].isin(cpfs_nao_encontrados)]
            st.write("Detalhes dos CPFs não encontrados:")
            st.dataframe(lista_nao_encontrados)
            # Usando BytesIO para exportar o Excel em memória
            output_nao_encontrados = io.BytesIO()
            lista_nao_encontrados.to_excel(output_nao_encontrados, index=False, engine='xlsxwriter')
            output_nao_encontrados.seek(0)
            st.download_button(
                label="Baixar CPFs não encontrados",
                data=output_nao_encontrados,
                file_name=f"nao_encontrados_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        pag['valor'] = pag['valor'].abs()
        pag_agrupado = pag.groupby('cpf', as_index=False)['valor'].sum()
        resultado = pd.merge(base_fixa, pag_agrupado, left_on=4, right_on='cpf', how='inner')
        resultado_agrupado = resultado.groupby('cpf', as_index=False).agg({
            0: 'first',
            1: 'first',
            2: 'first',
            3: 'first',
            'valor': 'sum'
        })
        layout_final = pd.DataFrame({
            'A': resultado_agrupado[0],
            'B': resultado_agrupado[1].astype(str).str.zfill(5),
            'C': resultado_agrupado[2].astype(str).str.zfill(1),
            'D': resultado_agrupado[3].str.upper().str.strip(),
            'E': resultado_agrupado['cpf'],
            'F': '1',
            'G': resultado_agrupado['valor'].fillna(0).round(2)
        })
        st.write(f"Arquivo final terá {len(layout_final)} registros")
        st.write(f"Valor total dos pagamentos: R$ {layout_final['G'].sum():,.2f}")
        st.dataframe(layout_final)
        # Usando BytesIO para exportar o Excel em memória
        layout_output = io.BytesIO()
        layout_final.to_excel(layout_output, index=False, header=False, engine='xlsxwriter')
        layout_output.seek(0)
        st.download_button(
            label="Baixar arquivo final",
            data=layout_output,
            file_name=f"layout_itau_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Erro: {str(e)}")
