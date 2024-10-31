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

# Função para encontrar grupos de URLs semelhantes
def encontrar_grupos_similares(grouped_df, percent):
    urls = grouped_df.index.tolist()
    grupos = []
    urls_processadas = set()
    
    for i, url in enumerate(urls):
        if url in urls_processadas:
            continue
        grupo = [url]
        urls_processadas.add(url)
        kwds_url = grouped_df.at[url, 'Query']
        
        for j in range(i + 1, len(urls)):
            outra_url = urls[j]
            if outra_url in urls_processadas:
                continue
            kwds_outra = grouped_df.at[outra_url, 'Query']
            termos_compartilhados = kwds_url.intersection(kwds_outra)
            percentual_similaridade = len(termos_compartilhados) / len(kwds_url)
            if percentual_similaridade >= percent:
                grupo.append(outra_url)
                urls_processadas.add(outra_url)
        
        if len(grupo) > 1:
            grupos.append(grupo)
    
    return grupos

# Função para processar os grupos e determinar a URL a manter
def processar_grupos(grupos, grouped_df):
    resultados = []
    for grupo in grupos:
        # Combinar todas as queries do grupo para encontrar termos compartilhados
        termos_compartilhados = set.intersection(*(grouped_df.at[url, 'Query'] for url in grupo))
        numero_termos_compartilhados = len(termos_compartilhados)
        
        # Determina qual URL manter (URL com maior número de cliques)
        cliques_urls = grouped_df.loc[grupo, 'Url Clicks']
        url_a_manter = cliques_urls.idxmax()
        cliques_a_manter = cliques_urls.max()
        
        # URLs semelhantes (todas as do grupo)
        urls_semelhantes = ', '.join(grupo)
        
        # Termos compartilhados como string separado por vírgulas
        termos_compartilhados_str = ', '.join(termos_compartilhados)
        
        resultados.append({
            'URLs Semelhantes': urls_semelhantes,
            'Termos Compartilhados': termos_compartilhados_str,
            '# Termos Compartilhados': numero_termos_compartilhados,
            'URL a Manter': url_a_manter,
            'Cliques': cliques_a_manter
        })
    return pd.DataFrame(resultados)

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
                
                # Encontra grupos de URLs semelhantes
                grupos_similares = encontrar_grupos_similares(grouped_df, percent)
                
                # Processa os grupos para determinar a URL a manter
                resultados_df = processar_grupos(grupos_similares, grouped_df)
                
                if not resultados_df.empty:
                    st.success("Processamento concluído!")
                    st.dataframe(resultados_df[['URLs Semelhantes', 'Termos Compartilhados', 
                                                '# Termos Compartilhados', 
                                                'URL a Manter', 'Cliques']])
                    
                    # Permitir download dos resultados
                    csv = resultados_df[['URLs Semelhantes', 'Termos Compartilhados', 
                                         '# Termos Compartilhados', 
                                         'URL a Manter', 'Cliques']].to_csv(index=False).encode('utf-8')
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
