import streamlit as st
import pandas as pd
import time  # Importado para simulação de tempo no progresso

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
    
    # Upload do arquivo
    uploaded_file = st.file_uploader("Carregue o arquivo CSV com os dados do GSC", type="csv")
    
    if uploaded_file:
        # Percentual de similaridade
        percent = st.slider("Percentual mínimo de similaridade de keywords:", 0.1, 1.0, 0.8)
        
        # Carregar os dados
        gsc_data = load_data(uploaded_file)
        st.write("Dados carregados com sucesso.")
        
        # Agrupar keywords por URL
        kwd_by_urls_df = group_keywords(gsc_data)
        st.write("Agrupamento das keywords por URL concluído.")
        
        # Barra de progresso
        progress_bar = st.progress(0)
        total_rows = len(kwd_by_urls_df)
        
        # Identificar URLs semelhantes e número de keywords semelhantes com progresso
        for i, row in kwd_by_urls_df.iterrows():
            kwd_by_urls_df.at[row.name, ['URLs Semelhantes', 'Nº de Keywords Semelhantes']] = keywords_similares(row, kwd_by_urls_df, percent)
            progress_bar.progress((i + 1) / total_rows)
        
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
