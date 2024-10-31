import streamlit as st
import pandas as pd

# Função para carregar os dados do arquivo CSV
@st.cache_data
def load_data(file):
    gsc_data = pd.read_csv(file)
    gsc_data = gsc_data[~gsc_data['Landing Page'].str.contains("#")]
    return gsc_data

# Função para agrupar as keywords por URL e somar o número de cliques
@st.cache_data
def group_keywords(gsc_data):
    kwd_by_urls = gsc_data.groupby('Landing Page').agg({'Query': list, 'Url Clicks': 'sum'})
    kwd_by_urls_df = pd.DataFrame(kwd_by_urls)
    return kwd_by_urls_df

# Função principal do app
def main():
    st.title("Encontre páginas semelhantes com dados do GSC")

    with st.expander("Leia antes de usar"):
        st.write("""
        **Como conseguir os dados do GSC?**

        1. Crie um dashboard no Looker Studio com o gráfico de 'Tabela'.
        2. Na tabela, insira como dimensão os campos Landing Page e Query.
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
    
    # Percentual de similaridade
    percent = st.slider("Percentual mínimo de similaridade de keywords para identificar URLs competindo entre si:", 0.1, 1.0, 0.8)
    
    if uploaded_file:
        if st.button("Iniciar Análise"):
            with st.spinner("Processando os dados..."):
                
                # Carregar os dados
                gsc_data = load_data(uploaded_file)
                
                # Agrupar keywords por URL
                kwd_by_urls_df = group_keywords(gsc_data)
                
                # Filtrar URLs com menos de 10 keywords
                kwd_by_urls_df = kwd_by_urls_df[kwd_by_urls_df['Query'].apply(lambda x: len(x) >= 10)]
                
                # Gerar um mapeamento para contar as keywords semelhantes e evitar `apply`
                keyword_sets = kwd_by_urls_df['Query'].apply(set)
                
                similar_urls = []
                num_keywords_similar = []
                url_to_keep = []
                
                for i, (url, keywords) in enumerate(keyword_sets.items()):
                    similar, count = [], []
                    max_clicks = kwd_by_urls_df.loc[url, 'Url Clicks']
                    best_url = url

                    for comp_url, comp_keywords in keyword_sets.items():
                        if url != comp_url:
                            shared_keywords = keywords.intersection(comp_keywords)
                            if len(shared_keywords) >= percent * len(keywords):
                                similar.append(comp_url)
                                count.append(len(shared_keywords))
                                
                                # Comparar os cliques para decidir a URL a manter
                                comp_clicks = kwd_by_urls_df.loc[comp_url, 'Url Clicks']
                                if comp_clicks > max_clicks:
                                    max_clicks = comp_clicks
                                    best_url = comp_url
                    
                    similar_urls.append(similar)
                    num_keywords_similar.append(count)
                    url_to_keep.append(best_url)
                
                kwd_by_urls_df['URLs Semelhantes'] = similar_urls
                kwd_by_urls_df['Nº de Keywords Semelhantes'] = num_keywords_similar
                kwd_by_urls_df['URL para Manter'] = url_to_keep
                
                # Exibir o resultado
                display_columns = ['Query', 'URLs Semelhantes', 'Nº de Keywords Semelhantes', 'Url Clicks', 'URL para Manter']
                st.success("Processamento concluído!")
                st.write("Resultado da Análise:")
                st.dataframe(kwd_by_urls_df[display_columns])

if __name__ == "__main__":
    main()
