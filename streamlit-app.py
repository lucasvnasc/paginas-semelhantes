import pandas as pd
import streamlit as st
import time

# Importação de dados do GSC. Colunas necessárias: Landing Page, Query e Url Clicks
def load_data(file):
    gsc_data = pd.read_csv(file)
    gsc_data = gsc_data[~gsc_data['Landing Page'].str.contains("#")]
    return gsc_data

# Agrupamento de keywords e cliques por URL
def group_keywords(gsc_data):
    kwd_by_urls = gsc_data.groupby('Landing Page').agg({'Query': list, 'Url Clicks': 'sum'})
    kwd_by_urls_df = pd.DataFrame(kwd_by_urls)
    return kwd_by_urls_df

# Função que irá checar as páginas ranqueando para os mesmos termos e contar as keywords semelhantes
def keywords_similares(row, kwd_by_urls_df, percent):
    url_atual = row.name
    kwds_atuais = set(row['Query'])
    
    if len(kwds_atuais) < 10:
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

# Função para identificar a URL com mais cliques e marcar a outra para descartar
def select_url_to_keep(row, kwd_by_urls_df):
    urls_similares = row['URLs Semelhantes']
    if not urls_similares:
        return None
    
    max_clicks = row['Url Clicks']
    url_to_keep = row.name
    
    for url in urls_similares:
        clicks = kwd_by_urls_df.loc[url, 'Url Clicks']
        if clicks > max_clicks:
            max_clicks = clicks
            url_to_keep = url
    
    return url_to_keep

def main():
    st.title("Encontre páginas semelhantes com dados do GSC")

    with st.expander("Leia antes de usar"):
        st.write("""
        **Como conseguir os dados do GSC?**

        1. Crie um dashboard no Looker Studio com o gráfico de 'Tabela'.
        2. Na tabela, insira como dimensão os campos Landing Page, Query e Url clicks.
        3. Filtre o período que deseja coletar os dados (sugestão: últimos 30 dias)
        4. Nos três pontos da tabela, clique em exportar para CSV.
        Verifique se o arquivo .csv exportado possui as colunas Landing Page e Query (nomeadas exatamente desta forma)

        **Por que exportar os dados pelo Looker Studio?**
        
        O Search Console possui uma limitação de 1000 linhas. No Looker Studio, você pode expandir essa limitação, conseguindo exportar quase tudo que precisa.
        Porém, ainda assim existe limitação. Portanto, a depender do tamanho do seu site, alguns dados podem ser truncados. O ideal é exportar via BigQuery ou outra solução de big data que permita extrair os dados do GSC.
        
        **O que é a porcentagem pedida?**

        Define o número de keywords que uma página compartilha com as demais. Por padrão, definimos 80%. Então, o app vai verificar com quais outras URLs uma determinada página compartilha, no mínimo, 80% das keywords. Se for abaixo de 80%, não será considerado.
        """)

    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    percent = st.slider('Porcentagem de palavras compartilhadas', min_value=0.0, max_value=1.0, value=0.8, step=0.01)
    
    if st.button('Iniciar'):
        if uploaded_file is not None:
            progress_bar = st.progress(0)
            
            gsc_data = load_data(uploaded_file)
            progress_bar.progress(33)
            
            kwd_by_urls_df = group_keywords(gsc_data)
            progress_bar.progress(66)
            
            # Aplicação da função e criação das colunas de URLs semelhantes e nº de keywords semelhantes
            kwd_by_urls_df[['URLs Semelhantes', 'Nº de Keywords Semelhantes']] = kwd_by_urls_df.apply(
                lambda row: keywords_similares(row, kwd_by_urls_df, percent),
                axis=1,
                result_type="expand"
            )
            kwd_by_urls_df = kwd_by_urls_df[kwd_by_urls_df['URLs Semelhantes'].apply(lambda x: len(x) != 0)]
            
            # Seleção da URL a ser mantida
            kwd_by_urls_df['URL para Manter'] = kwd_by_urls_df.apply(select_url_to_keep, args=(kwd_by_urls_df,), axis=1)
            
            progress_bar.progress(100)
            st.write(kwd_by_urls_df[['Query', 'URLs Semelhantes', 'Nº de Keywords Semelhantes', 'Url Clicks', 'URL para Manter']])
        else:
            st.error('Por favor, faça o upload de um arquivo CSV.')

if __name__ == "__main__":
    main()
