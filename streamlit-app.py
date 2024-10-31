import pandas as pd
import streamlit as st
import time

# Importação de dados do GSC. Colunas necessárias: Landing Page, Query e Url clicks
def load_data(file):
    gsc_data = pd.read_csv(file)
    gsc_data = gsc_data[~gsc_data['Landing Page'].str.contains("#")]
    return gsc_data

# Agrupamento de keywords e cliques por URL
def group_keywords(gsc_data):
    kwd_by_urls = gsc_data.groupby('Landing Page')['Query'].apply(list)
    clicks_by_urls = gsc_data.groupby('Landing Page')['Url clicks'].sum()
    kwd_by_urls_df = pd.DataFrame(kwd_by_urls)
    kwd_by_urls_df['Total Clicks'] = clicks_by_urls
    return kwd_by_urls_df

# Função para checar páginas com keywords compartilhadas e somar cliques apenas das keywords comuns
def keywords_similares(row, gsc_data, kwd_by_urls_df, percent):
    url_atual = row.name
    kwds_atuais = set(row['Query'])
    
    if len(kwds_atuais) < 10:
        return [], None  # Retorna vazio e sem URL a ser mantida
    
    urls_similares = []
    max_clicks = 0
    url_to_keep = url_atual  # Inicializa com a URL atual

    for url, queries in kwd_by_urls_df['Query'].items():
        if url != url_atual:
            kwds_compartilhadas = kwds_atuais.intersection(set(queries))
            if len(kwds_compartilhadas) >= percent * len(kwds_atuais):
                urls_similares.append(url)

                # Soma os cliques das keywords compartilhadas
                cliques_compartilhados = gsc_data[(gsc_data['Landing Page'] == url) & 
                                                  (gsc_data['Query'].isin(kwds_compartilhadas))]['Url clicks'].sum()
                
                # Atualiza a URL a ser mantida caso encontre mais cliques nas keywords compartilhadas
                if cliques_compartilhados > max_clicks:
                    max_clicks = cliques_compartilhados
                    url_to_keep = url

    return urls_similares, url_to_keep

def main():
    st.title("Encontre páginas semelhantes com dados do GSC")

    with st.expander("Leia antes de usar"):
        st.write("""
        **Como conseguir os dados do GSC?**
        ...
        """)

    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    percent = st.slider('Porcentagem de palavras compartilhadas', min_value=0.0, max_value=1.0, value=0.8, step=0.01)
    
    if st.button('Iniciar'):
        if uploaded_file is not None:
            # Inicia a barra de progresso
            progress_bar = st.progress(0)
            
            gsc_data = load_data(uploaded_file)
            progress_bar.progress(33)
            
            kwd_by_urls_df = group_keywords(gsc_data)
            progress_bar.progress(66)
            
            # Aplicação da função acima e seleção da URL com mais cliques nas keywords compartilhadas
            kwd_by_urls_df['URLs Semelhantes'], kwd_by_urls_df['URL a ser mantida'] = zip(
                *kwd_by_urls_df.apply(keywords_similares, args=(gsc_data, kwd_by_urls_df, percent), axis=1)
            )
            kwd_by_urls_df = kwd_by_urls_df[kwd_by_urls_df['URLs Semelhantes'].apply(lambda x: len(x) != 0)]
            
            progress_bar.progress(100)
            
            st.write(kwd_by_urls_df)
        else:
            st.error('Por favor, faça o upload de um arquivo CSV.')

if __name__ == "__main__":
    main()
