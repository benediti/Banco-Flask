from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import pandas as pd
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecret"  # Para mensagens flash
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def normalizar_cpf(cpf):
    if pd.isna(cpf):
        return None
    import re
    cpf_str = re.sub(r'[^\d]', '', str(cpf).strip())
    if len(cpf_str) > 0 and len(cpf_str) <= 11:
        cpf_str = cpf_str.zfill(11)
    return cpf_str if len(cpf_str) == 11 else None

@app.route('/', methods=['GET', 'POST'])
def index():
    log = []
    if request.method == 'POST':
        base_file = request.files.get('base_file')
        pag_file = request.files.get('pag_file')
        if not base_file or base_file.filename == "":
            flash("Base de Funcionários não enviada.")
            return redirect(url_for('index'))
        if not pag_file or pag_file.filename == "":
            flash("Arquivo de pagamentos não enviado.")
            return redirect(url_for('index'))

        base_path = os.path.join(UPLOAD_FOLDER, secure_filename(base_file.filename))
        pag_path = os.path.join(UPLOAD_FOLDER, secure_filename(pag_file.filename))
        base_file.save(base_path)
        pag_file.save(pag_path)

        try:
            log.append("Iniciando processamento...")
            base = pd.read_excel(base_path, header=None, dtype=str)
            log.append(f"Base fixa carregada: {base.shape[0]} linhas, {base.shape[1]} colunas.")
            pag = pd.read_excel(pag_path, dtype={'CPF/CNPJ': str})
            log.append(f"Arquivo de pagamentos lido: {pag.shape[0]} linhas, {pag.shape[1]} colunas.")
            pag = pag.rename(columns={'CPF/CNPJ': 'cpf', 'Valor categoria/centro de custo': 'valor'})
            if 'cpf' not in pag.columns or 'valor' not in pag.columns:
                log.append("Colunas obrigatórias 'cpf' ou 'valor' não encontradas no arquivo de pagamentos.")
                flash("Colunas obrigatórias 'cpf' ou 'valor' não encontradas no arquivo de pagamentos.")
                return render_template('index.html', log=log)

            # Normalizar CPFs
            pag['cpf_original'] = pag['cpf'].copy()
            pag['cpf'] = pag['cpf'].apply(normalizar_cpf)
            base['cpf_original'] = base[4].copy()
            base[4] = base[4].apply(normalizar_cpf)
            pag = pag[pag['cpf'].notna()]
            base = base[base[4].notna()]
            log.append(f"Pagamentos: {len(pag)} válidos")
            log.append(f"Base: {len(base)} válidos")

            cpfs_base = set(base[4])
            cpfs_pag = set(pag['cpf'])
            cpfs_nao_encontrados = cpfs_pag - cpfs_base
            log.append(f"CPFs não encontrados na base: {len(cpfs_nao_encontrados)}")
            if cpfs_nao_encontrados:
                lista_nao_encontrados = pag[pag['cpf'].isin(cpfs_nao_encontrados)]
                log.append(f"{len(lista_nao_encontrados)} registros não encontrados na base.")

            pag['valor'] = pag['valor'].abs()
            pag_agrupado = pag.groupby('cpf', as_index=False)['valor'].sum()
            resultado = pd.merge(base, pag_agrupado, left_on=4, right_on='cpf', how='inner')
            if len(resultado) == 0:
                log.append("Nenhum CPF foi encontrado no merge. Verifique os dados.")
                flash("Nenhum CPF foi encontrado no merge.")
                return render_template('index.html', log=log)

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

            data = datetime.now().strftime('%Y%m%d')
            output_file = os.path.join(UPLOAD_FOLDER, f'layout_itau_{data}.xlsx')
            with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                layout_final.to_excel(writer, index=False, header=False, sheet_name='Sheet1')
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']
                valor_format = workbook.add_format({'num_format': '#,##0.00'})
                worksheet.set_column('G:G', None, valor_format)
            log.append(f"Arquivo gerado com sucesso: {output_file}")
            return send_file(output_file, as_attachment=True)

        except Exception as e:
            log.append(f"Erro: {str(e)}")
            flash(f"Erro: {str(e)}")
            return render_template('index.html', log=log)
    return render_template('index.html', log=log)

if __name__ == '__main__':
    app.run(debug=True)