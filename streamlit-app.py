import streamlit as st
import pandas as pd

# Função para carregar os dados do arquivo CSV
def load_data(file):
    gsc_data = pd.read_csv(file)
    gsc_data = gsc_data[~gsc_data['Landing Page'].str.contains("#")]
    return gsc_data

# Função para agrupar as keywords por URL e somar o número de cliques
def group_keywords(gsc_data):
    kwd_by_urls = gsc_data.groupby('Landing Page').agg({'Query': list, 'Url Clicks': 'sum'})
    kwd_by_urls_df = pd.DataFrame(kwd_by_urls)
    return kwd_by_urls_df

# Função que verifica URLs que compartilham keywords similares
def keywords_similares(row, kwd_by_urls_df, percent):
    url_atual = row.name
    kwds_atuais = set(row['Query'])
    
    if len(kwds_atuais) < 10:  # Ignorar URLs com menos de 10 keywords
        return [], []
    
    urls_similares = []
    num_keywords_semelhantes = []

    for url, data in kwd_by_urls_df.iterrows():
        queries = data['Query']
        if url != url_atual:
            kwds_compartilhadas = set(queries).intersection(kwds_atuais)
            if len(kwds_compartilhadas) >= percent * len(kwds_atuais):
                urls_similares.append(url)
                num_keywords_semelhantes.append(len(kwds_compartilhadas))
    
    return urls_similares, num_keywords_semelhantes

# Função para selecionar a URL com mais cliques e definir como a URL a ser mantida
def select_url_to_keep(row, kwd_by_urls_df):
    urls_similares = row['URLs Semelhantes']
    if not urls_similares:
        return None
    
    max_clicks = row['Url Clicks']
    url_to_keep = row.name
    
    for url in urls_similares:
        if url in kwd_by_urls_df.index:  # Verificar se a URL existe no DataFrame
            clicks = kwd_by_urls_df.loc[url, 'Url Clicks']
            if clicks > max_clicks:
                max_clicks = clicks
                url_to_keep = url
    
    return url_to_keep

# Função principal do app
def main():
    st.title("Análise de URLs por Keywords Similares")
    
    # Instruções
    st.write("""
        Este aplicativo ajuda a identificar URLs que compartilham um volume significativo de keywords similares,
        indicando URLs que podem estar competindo entre si no Google. 
        Carregue um arquivo CSV contendo as colunas "Landing Page", "Query" e "Url Clicks".
    """)
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("Carregue o arquivo CSV com os dados do GSC", type="csv")
    
    if uploaded_file:
        # Percentual de similaridade
        percent = st.slider("Percentual mínimo de similaridade de keywords para identificar URLs competindo entre si:", 0.1, 1.0, 0.8)
        
        # Carregar os dados
        gsc_data = load_data(uploaded_file)
        st.write("Dados carregados com sucesso.")
        
        # Agrupar keywords por URL
        kwd_by_urls_df = group_keywords(gsc_data)
        st.write("Agrupamento das keywords por URL concluído.")
        
        # Identificar URLs semelhantes e número de keywords semelhantes
        kwd_by_urls_df[['URLs Semelhantes', 'Nº de Keywords Semelhantes']] = kwd_by_urls_df.apply(
            lambda row: keywords_similares(row, kwd_by_urls_df, percent),
            axis=1,
            result_type="expand"
        )
        
        # Filtrar para apenas URLs com semelhantes
        kwd_by_urls_df = kwd_by_urls_df[kwd_by_urls_df['URLs Semelhantes'].apply(lambda x: len(x) != 0)]
        
        # Selecionar a URL a ser mantida
        kwd_by_urls_df['URL para Manter'] = kwd_by_urls_df.apply(select_url_to_keep, args=(kwd_by_urls_df,), axis=1)
        
        # Exibir o resultado
        display_columns = ['Query', 'URLs Semelhantes', 'Nº de Keywords Semelhantes', 'Url Clicks', 'URL para Manter']
        st.write("Resultado da Análise:")
        st.dataframe(kwd_by_urls_df[display_columns])

if __name__ == "__main__":
    main()
