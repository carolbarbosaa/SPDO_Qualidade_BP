import streamlit as st
import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    "Críticas BP",
    layout="wide",
    page_icon="📈",
)

# Path
path = Path(__file__).parent
data_path = path / "Data"

@st.cache_data()
def read_data(file_path):
    df = pd.read_csv(file_path, sep=",", encoding="utf-8", decimal=".", low_memory=False,
                     parse_dates=["DATA_PRECO"], dtype={"INS_INF": str, "INSUMO": str, "TP_PRECO": str, "PRECO": float, "INFORMANTE": str})
    df.drop_duplicates(["INS_INF","DATA_PRECO"], inplace=True)
    return df

# def read_data(file_path):
#     df = pd.read_excel(file_path, parse_dates=["DATA_PRECO"], dtype={"INS_INF": str, "INSUMO": str, "TP_PRECO": str, "PRECO": float})
#     df.drop_duplicates(["INS_INF","DATA_PRECO"], inplace=True)
#     return df

@st.cache_data()
def process_data(df, n_desvios):

    # Criação da média móvel
    df['MEDIA_MOVEL'] = df.groupby('INSUMO')['MEDIANA_PRECO'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())

    # Cálculo do desvio padrão
    df['DESVIO_PADRAO'] = df.groupby('INSUMO')['MEDIANA_PRECO'].transform(lambda x: x.rolling(window=6, min_periods=2).std())

    # Calcular os limites inferior e superior do intervalo de confiança
    df['LIMITE_INFERIOR'] = df['MEDIA_MOVEL'] - n_desvios * df['DESVIO_PADRAO']
    df['LIMITE_SUPERIOR'] = df['MEDIA_MOVEL'] + n_desvios * df['DESVIO_PADRAO']

    # Shift dos limites para comparar o preço atual com os limites do dia anterior
    df['limite_inferior_anterior'] = df.groupby('INSUMO')['LIMITE_INFERIOR'].shift(1)
    df['limite_superior_anterior'] = df.groupby('INSUMO')['LIMITE_SUPERIOR'].shift(1) 

    return df

def verificar_limites(df):
    # Verifica se o preço está dentro dos limites do dia anterior
    df['dentro_limites'] = ((df['PRECO'] >= df['limite_inferior_anterior']) & 
                            (df['PRECO'] <= df['limite_superior_anterior']))

    return df

def plot(df_insinf, df):
    
    # Verificando se há informações sobre limite superior e inferior anterior
    if df_insinf[~df_insinf["limite_inferior_anterior"].isna()].shape[0] > 0:
        # Create the scatter plot
        df_insinf_dentro = df_insinf[df_insinf['dentro_limites'] == True]
        fig = px.scatter(df_insinf_dentro, x=df_insinf_dentro['DATA_PRECO'], y=df_insinf_dentro['PRECO'], title='Gráfico de Dispersão com Médias e Limites', hover_data={'INS_INF': True})

        # Add moving average line
        fig.add_scatter(x=df['DATA_PRECO'], y=df['MEDIA_MOVEL'].shift(1), mode='lines', name='Média Móvel')

        # Add lower and upper limit lines
        fig.add_scatter(x=df['DATA_PRECO'], y=df['LIMITE_INFERIOR'].shift(1), mode='lines', fill='tonexty', name='Limite Inferior')
        fig.add_scatter(x=df['DATA_PRECO'], y=df['LIMITE_SUPERIOR'].shift(1), mode='lines', fill='tonexty', name='Limite Superior')

        # Highlight prices outside the limit
        fig.add_scatter(x=df_insinf[df_insinf['dentro_limites'] == False]['DATA_PRECO'], y=df_insinf[df_insinf['dentro_limites'] == False]['PRECO'],
                        mode='markers', name='Preços Fora do Limite', marker=dict(color='red'), text=["Insumo informado: {}".format(ins_inf) for ins_inf in df_insinf['INS_INF']], hoverinfo = ['text'])

    else:
        fig = px.scatter(df_insinf, x=df_insinf['DATA_PRECO'], y=df_insinf['PRECO'], title='Gráfico de Dispersão com Médias e Limites', hover_data={'INS_INF': True})

    return fig



# Chamar a função para carregar e processar os dados
df_old = read_data(data_path / "CRITICA BP_PILOTO.csv")

# Ordena os dados por insumo e data
df_old.sort_values(by=['INSUMO', 'DATA_PRECO'], ascending=[True, True], inplace=True)

# UI #
st.title("Críticas BP")

st.sidebar.title("Menu")

# Filtrando os dados
insumos = df_old["INSUMO"].unique()
insumo = st.sidebar.selectbox("Selecione um insumo:", insumos, format_func=lambda x: x + " - " + df_old[df_old["INSUMO"] == x]["NM_INSUMO"].iloc[0])
df_old = df_old[(df_old["INSUMO"] == insumo)].reset_index(drop=True) 


ins_infs = sorted(list(df_old["INS_INF"].unique()))
ins_inf = st.sidebar.multiselect('Selecione o insumo informado:', ins_infs, placeholder = "Todas as opções")
if not ins_inf:
    df_old = df_old
else:
    df_old = df_old[df_old["INS_INF"].isin(ins_inf)].reset_index(drop=True) 


tipo_precos = sorted(list(df_old["TP_PRECO"].unique()))
tipo_preco = st.sidebar.multiselect('Selecione o tipo de preço:', tipo_precos, placeholder = "Todas as opções")
if not tipo_preco:
    df_old = df_old
else:
    df_old = df_old[df_old["TP_PRECO"].isin(tipo_preco)].reset_index(drop=True) 


tipo_estabelecimentos = sorted(list(df_old["TIPO_ESTABELECIMENTO"].unique()))
tipo_estabelecimento = st.sidebar.multiselect('Selecione o tipo de estabelecimento:', tipo_estabelecimentos, placeholder = "Todas as opções")
if not tipo_estabelecimento:
    df_old = df_old
else:
    df_old = df_old[df_old["TIPO_ESTABELECIMENTO"].isin(tipo_estabelecimento)].reset_index(drop=True) 


regioes = sorted(list(df_old["REGIAO"].unique()))
regiao = st.sidebar.multiselect('Selecione a região:', regioes, placeholder = "Todas as opções")
if not regiao:
    df_old = df_old
else:
    df_old = df_old[df_old["REGIAO"].isin(regiao)].reset_index(drop=True) 


ufs = sorted(list(df_old["UF"].unique()))
uf = st.sidebar.multiselect('Selecione a UF:', ufs, placeholder = "Todas as opções")
if not uf:
    df_old = df_old
else:
    df_old = df_old[df_old["UF"].isin(uf)].reset_index(drop=True) 

desvios = st.sidebar.slider("Desvios Padrão", min_value = 1.0, max_value = 4.0, step = 0.5, value = 2.5)

###
# Criação da mediana dos insumos
df_old['MEDIANA_PRECO'] = df_old.groupby(['INSUMO', 'DATA_PRECO'])['PRECO'].transform('median')

# Criar um novo DataFrame contendo apenas as colunas desejadas
df_new = df_old[['DATA_PRECO', 'INSUMO', 'NM_INSUMO', 'MEDIANA_PRECO']]

# Remover linhas duplicadas
df_new.drop_duplicates(inplace=True)

# Resetar os índices
df_new.reset_index(drop=True, inplace=True)

# Processando os dados
df = process_data(df=df_new, n_desvios=desvios)

# Combinando as bases
df_insinf = pd.merge(df_old, df, on = ['INSUMO', 'DATA_PRECO'], how = 'left')
df_insinf.drop(columns=['MEDIANA_PRECO_y', 'NM_INSUMO_y'], inplace=True)
df_insinf.rename(columns={'MEDIANA_PRECO_x': 'MEDIANA_PRECO', 'NM_INSUMO_x': 'NM_INSUMO'}, inplace=True)

# Verificando se o preço do insumo informado está dentro dos limites
df_insinf = df_insinf.groupby('INSUMO').apply(verificar_limites).reset_index(drop=True)

# Criando o gráfico
fig = plot(df_insinf, df)
st.plotly_chart(fig, use_container_width=True)

if df_insinf[~df_insinf["limite_inferior_anterior"].isna()].shape[0] > 0:
    # Mostrando um indicador com total de preços um passo a frente dentro e fora do intervalo de confiança
    total = len(df_insinf)
    total_dentro = len(df_insinf[df_insinf['dentro_limites'] == True])
    total_fora = len(df_insinf[df_insinf['dentro_limites'] == False])
    st.write(f"Total de preços um passo a frente: {total}")
    st.write(f"Total de preços um passo a frente <b>dentro</b> do intervalo de confiança: {total_dentro}", unsafe_allow_html=True)
    st.write(f"Total de preços um passo a frente <b>fora</b> do intervalo de confiança: {total_fora}", unsafe_allow_html=True)

    st.write("### Preços que ficaram de fora da cerca")
    st.write(df_insinf[df_insinf['dentro_limites'] == False].sort_values(by='DATA_PRECO', ascending=False).drop(['LIMITE_SUPERIOR', 'LIMITE_INFERIOR','MEDIA_MOVEL','DESVIO_PADRAO'], axis=1))

    st.write("### Tabela agregada")
    df_agregado = df_old.groupby('INS_INF')['PRECO'].agg(['count', 'mean', 'std'])   
    df_agregado['CV'] = df_agregado['std'] / df_agregado['mean']
    df_foralimites = df_insinf[df_insinf['dentro_limites'] == False].groupby('INS_INF')['PRECO'].count()
    df_agregado_final = pd.merge(df_agregado, df_foralimites, on = ['INS_INF'], how = 'left')
    df_agregado_final.rename(columns={'count': 'Quantidade de Preços', 'mean': 'Média', 'std': 'Desvio Padrão', 'PRECO': 'Quantidade de Preços Fora da Cerca'}, inplace=True)
    df_agregado_final['Quantidade de Preços Fora da Cerca'].fillna(0, inplace=True)
    df_agregado_final = df_agregado_final[['Quantidade de Preços', 'Quantidade de Preços Fora da Cerca', 'Média', 'Desvio Padrão', 'CV']]
    st.write(df_agregado_final)

else:
    st.write("### Tabela agregada")
    df_agregado = df_old.groupby('INS_INF')['PRECO'].agg(['count', 'mean', 'std'])   
    df_agregado['CV'] = df_agregado['std'] / df_agregado['mean']
    df_agregado.rename(columns={'count': 'Quantidade de Preços', 'mean': 'Média', 'std': 'Desvio Padrão'}, inplace=True)
    st.write(df_agregado)


# st.write('old')
# st.write(df_old)
# st.write('new')
# st.write(df_new)
# st.write('df')
# st.write(df)
# st.write('insinf')
# st.write(df_insinf)
