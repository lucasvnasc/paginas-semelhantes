import pandas as pd
import streamlit as st
from collections import defaultdict
from joblib import Parallel, delayed
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import jaccard_score

# Caching das funções para melhorar a performance
@st.cache_data
def load_data(file):
    gsc_data = pd.read_csv(file, dtype={
        'Landing Page': 'category',
        'Query': 'category',
        'Url Clicks': 'int32'
    })
    # Filtra URLs que não contêm '#'
    gsc_data = gsc_data[~gsc_data['Landing Page'].str.contains("#")]
    return gsc_data

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

@st.cache_data
def create_inverted_index(grouped_df):
    inverted_index = defaultdict(set)
    for url, keywords in grouped_df['Query'].items():
        for keyword in keywords:
            inverted_index[keyword].add(url)
    return inverted_index

def process_url(url, grouped_df, inverted_index, percent, urls_processadas):
    if url in urls_processadas:
        return None
    row = grouped_df.loc[url]
    kwds_atuais = row['Query']
    num_kwds = len(kwds_atuais)
    min_shared = int(percent * num_kwds)
    
    if num_kwds < 10:
        return None
    
    similares_info = []
    urls_potential = set()
    
    # Utilizar o index invertido para encontrar URLs que compartilham keywords
    for kw in kwds_atuais:
        urls_potential.update(inverted_index[kw])
    
    urls_potential.discard(url)  # Remover a própria URL
    
    for similar_url in urls_potential:
        kwds_compartilhadas = grouped_df.at[url, 'Query'].intersection(grouped_df.at[similar_url, 'Query'])
        quantidade_compartilhada = len(kwds_compartilhadas)
        if quantidade_compartilhada >= min_shared:
            similares_info.append({
                'URL Semelhante': similar_url,
                'Termos Compartilhados': list(kwds_compartilhadas),
                'Quantidade de Termos Compartilhados': quantidade_compartilhada
            })
    
    if not similares_info:
        return None
    
    # Determina qual URL manter (URL com maior número de cliques)
    todas_urls = [url] + [info['URL Semelhante'] for info in similares_info]
    cliques_urls = grouped_df.loc[todas_urls, 'Url Clicks']
    url_a_manter = cliques_urls.idxmax()
    cliques_a_manter = cliques_urls.max()
    
    # Atualiza o conjunto de URLs processadas
    urls_processadas.update(todas_urls)
    
    return {
        'URL': url,
        'URLs Semelhantes': [info['URL Semelhante'] for info in similares_info],
        'Termos Compartilhados': [info['Termos Compartilhados'] for info in similares_info],
        'Quantidade de Termos Compartilhados': [info['Quantidade de Termos Compartilhados'] for info in similares_info],
        'URL a Manter': url_a_manter,
        'Cliques da URL a Manter': cliques_a_manter
    }

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
                
                # Cria o index invertido
                inverted_index = create_inverted_index(grouped_df)
                
                # Inicializa o conjunto de URLs já processadas
                urls_processadas = set()
                
                # Paraleliza o processamento das URLs
                resultados = Parallel(n_jobs=-1)(
                    delayed(process_url)(url, grouped_df, inverted_index, percent, urls_processadas) 
                    for url in grouped_df.index
                )
                
                # Filtra resultados nulos
                resultados = [res for res in resultados if res is not None]
                
                # Cria um DataFrame para exibir os resultados
                if resultados:
                    resultados_df = pd.DataFrame(resultados)
                    st.success("Processamento concluído!")
                    st.dataframe(resultados_df)
                    
                    # Permitir download dos resultados
                    csv = resultados_df.to_csv(index=False).encode('utf-8')
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
