import pandas as pd
import streamlit as st

# Função para validar e limpar os dados
def validate_and_clean_data(gsc_data):
    # Remover linhas com valores ausentes nas colunas essenciais
    gsc_data = gsc_data.dropna(subset=['Landing Page', 'Query', 'Url Clicks'])
    
    # Remover duplicatas
    gsc_data = gsc_data.drop_duplicates()
    
    # Converter URLs para formato consistente (por exemplo, remover trailing slashes)
    gsc_data['Landing Page'] = gsc_data['Landing Page'].str.rstrip('/')
    
    # Padronizar keywords para minúsculas
    gsc_data['Query'] = gsc_data['Query'].str.lower()
    
    # Garantir que 'Url Clicks' seja inteiro positivo
    gsc_data = gsc_data[gsc_data['Url Clicks'] >= 0]
    
    return gsc_data

# Importação de dados do GSC. Colunas necessárias: Landing Page, Query e Url Clicks
@st.cache_data
def load_data(file):
    gsc_data = pd.read_csv(file, dtype={
        'Landing Page': 'category',
        'Query': 'category',
        'Url Clicks': 'int32'
    })
    # Filtra URLs que não contêm '#'
    gsc_data = gsc_data[~gsc_data['Landing Page'].str.contains("#")]
    
    # Valida e limpa os dados
    gsc_data = validate_and_clean_data(gsc_data)
    return gsc_data

# Agrupamento de keywords e cliques por URL
@st.cache_data
def group_data(gsc_data):
    # Agrupa as queries por Landing Page e converte para conjuntos
    kwd_by_urls = gsc_data.groupby('Landing Page')['Query'].apply(set)
    # Soma os cliques por Landing Page
    clicks_by_urls = gsc_data.groupby('Landing Page')['Url Clicks'].sum()
    # Combina ambos em um DataFrame
    grouped_df = pd.DataFrame({
        'Query': kwd_by_urls,
        'Url Clicks': clicks_by_urls
    })
    return grouped_df

# Função que irá checar as páginas ranqueando para os mesmos termos e determinar qual URL manter
def keywords_similares(row, grouped_df, percent):
    url_atual = row.name
    kwds_atuais = row['Query']
    clicks_atual = row['Url Clicks']
    
    if len(kwds_atuais) < 10:
        return pd.Series({
            'URLs Semelhantes': [],
            'Termos Compartilhados': [],
            'Quantidade de Termos Compartilhados': [],
            'URL a Manter': url_atual,
            'Cliques da URL a Manter': clicks_atual
        })
    
    similares_info = []
    
    for url, queries in grouped_df['Query'].items():
        if url != url_atual:
            kwds_compartilhadas = kwds_atuais.intersection(queries)
            quantidade_compartilhada = len(kwds_compartilhadas)
            percentual_similaridade = quantidade_compartilhada / len(kwds_atuais)
            if percentual_similaridade >= percent:
                similares_info.append({
                    'URL Semelhante': url,
                    'Termos Compartilhados': list(kwds_compartilhadas),
                    'Quantidade de Termos Compartilhados': quantidade_compartilhada
                })
    
    if not similares_info:
        return pd.Series({
            'URLs Semelhantes': [],
            'Termos Compartilhados': [],
            'Quantidade de Termos Compartilhados': [],
            'URL a Manter': url_atual,
            'Cliques da URL a Manter': clicks_atual
        })
    
    # Determina qual URL manter (URL com maior número de cliques)
    todas_urls = [url_atual] + [info['URL Semelhante'] for info in similares_info]
    cliques_urls = grouped_df.loc[todas_urls, 'Url Clicks']
    url_a_manter = cliques_urls.idxmax()
    cliques_a_manter = cliques_urls.max()
    
    # Filtra os similares que não são a URL a manter
    similares_final = [info for info in similares_info if info['URL Semelhante'] != url_a_manter]
    
    return pd.Series({
        'URLs Semelhantes': [info['URL Semelhante'] for info in similares_final],
        'Termos Compartilhados': [info['Termos Compartilhados'] for info in similares_final],
        'Quantidade de Termos Compartilhados': [info['Quantidade de Termos Compartilhados'] for info in similares_final],
        'URL a Manter': url_a_manter,
        'Cliques da URL a Manter': cliques_a_manter
    })

def main():
    st.title("Encontre páginas semelhantes com dados do GSC")
    
    with st.expander("Leia antes de usar"):
        st.write("""
        **Como conseguir os dados do GSC?**

        1. Crie um dashboard no Looker Studio com o gráfico de 'Tabela'.
        2. Na tabela, insira como dimensão os campos Landing Page, Query e Url Clicks.
        3. Filtre o período que deseja coletar os dados (sugestão: últimos 30 dias)
        4. Nos três pontos da tabela, clique em exportar para CSV.
        Verifique se o arquivo .csv exportado possui as colunas Landing Page, Query e Url Clicks (nomeadas exatamente desta forma)

        **Por que exportar os dados pelo Looker Studio?**
        
        O Search Console possui uma limitação de 1000 linhas. No Looker Studio, você pode expandir essa limitação, conseguindo exportar quase tudo que precisa.
        Porém, ainda assim existe limitação. Portanto, a depender do tamanho do seu site, alguns dados podem ser truncados. O ideal é exportar via BigQuery ou outra solução de big data que permita extrair os dados do GSC.
        
        **O que é a porcentagem pedida?**

        Define o número de keywords que uma página compartilha com as demais. Por padrão, definimos 80%. Então, o app vai verificar com quais outras URLs uma determinada página compartilha, no mínimo, 80% das keywords. Se for abaixo de 80%, não será considerado.

        **Como a URL a ser mantida é escolhida?**

        Quando duas ou mais URLs compartilham uma porcentagem significativa de keywords, a URL que será mantida é aquela que possui o maior número total de cliques. Isso ajuda a manter a página que está gerando mais tráfego.
        """)
    
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    percent = st.slider('Porcentagem de palavras compartilhadas', min_value=0.0, max_value=1.0, value=0.8, step=0.01)
    
    if st.button('Iniciar'):
        if uploaded_file is not None:
            with st.spinner('Processando...'):
                # Carrega os dados
                gsc_data = load_data(uploaded_file)
                
                # Agrupa as keywords e cliques por URL
                grouped_df = group_data(gsc_data)
                
                # Aplica a função de encontrar URLs similares e determinar qual manter
                resultados = grouped_df.apply(keywords_similares, axis=1, args=(grouped_df, percent))
                
                # Combina os resultados com o DataFrame original
                resultados_df = grouped_df.join(resultados)
                
                # Filtra apenas as URLs que têm URLs semelhantes
                resultados_filtrados = resultados_df[resultados_df['URLs Semelhantes'].map(len) > 0]
                
                if not resultados_filtrados.empty:
                    st.success("Processamento concluído!")
                    st.dataframe(resultados_filtrados[['URLs Semelhantes', 'Termos Compartilhados', 
                                                      'Quantidade de Termos Compartilhados', 
                                                      'URL a Manter', 'Cliques da URL a Manter']])
                    
                    # Permitir download dos resultados
                    csv = resultados_filtrados[['URLs Semelhantes', 'Termos Compartilhados', 
                                                'Quantidade de Termos Compartilhados', 
                                                'URL a Manter', 'Cliques da URL a Manter']].to_csv(index=True).encode('utf-8')
                    st.download_button(
                        label="Download dos Resultados",
                        data=csv,
                        file_name='resultados_seo.csv',
                        mime='text/csv',
                    )
                else:
                    st.warning("Nenhuma URL com URLs semelhantes encontrada com base nos critérios definidos.")
        else:
            st.error('Por favor, faça o upload de um arquivo CSV.')

if __name__ == "__main__":
    main()
