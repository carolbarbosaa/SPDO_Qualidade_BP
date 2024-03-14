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
def process_data(df,n_desvios=1.5):

    # Ordena os dados por insumo e data
    df.sort_values(by=['INS_INF', 'DATA_PRECO'], ascending=[True, True], inplace=True)

    # Criação da mediana móvel
    df['MEDIANA_MOVEL'] = df.groupby('INS_INF')['PRECO'].transform(lambda x: x.rolling(window=6, min_periods=1).median())

    # Criação da média móvel
    df['MEDIA_MOVEL'] = df.groupby('INS_INF')['PRECO'].transform(lambda x: x.rolling(window=3, min_periods=1).mean())

    # Cálculo do desvio padrão
    df['DESVIO_PADRAO'] = df.groupby('INS_INF')['PRECO'].transform(lambda x: x.rolling(window=6, min_periods=2).std())


    # Calcular os limites inferior e superior do intervalo de confiança
    #df['LIMITE_INFERIOR'] = df['MEDIANA_MOVEL'] - df['DESVIO_PADRAO']
    #df['LIMITE_SUPERIOR'] = df['MEDIANA_MOVEL'] + df['DESVIO_PADRAO']
    df['LIMITE_INFERIOR'] = df['MEDIA_MOVEL'] - n_desvios * df['DESVIO_PADRAO']
    df['LIMITE_SUPERIOR'] = df['MEDIA_MOVEL'] + n_desvios * df['DESVIO_PADRAO']

    df = df.groupby('INS_INF').apply(verificar_limites).reset_index(drop=True)

    return df

@st.cache_data()
def read_data(file_path):
    df = pd.read_csv(file_path, sep=",", encoding="utf-8", decimal=".", low_memory=False,
                        parse_dates=["DATA_PRECO"], dtype={"INS_INF": str, "INSUMO": str, "TP_PRECO": str, "PRECO": float})
    df.drop_duplicates(["INS_INF","DATA_PRECO"], inplace=True)
    return df

def verificar_limites(df):
    # Shift dos limites para comparar o preço atual com os limites do dia anterior
    df['limite_superior_anterior'] = df.groupby('INS_INF')['LIMITE_SUPERIOR'].shift(1)
    df['limite_inferior_anterior'] = df.groupby('INS_INF')['LIMITE_INFERIOR'].shift(1)

    # Verifica se o preço está dentro dos limites do dia anterior
    df['dentro_limites'] = ((df['PRECO'] >= df['limite_inferior_anterior']) & 
                            (df['PRECO'] <= df['limite_superior_anterior']))

    # Remove as colunas de limite anterior, se não forem mais necessárias
    #df.drop(['limite_superior_anterior', 'limite_inferior_anterior'], axis=1, inplace=True)

    return df


def plot(df):
    # Create the scatter plot
    fig = px.scatter(df, x='DATA_PRECO', y='PRECO', title='Gráfico de Dispersão com Médias e Limites')

    # Add moving average line
    fig.add_scatter(x=df['DATA_PRECO'], y=df['MEDIA_MOVEL'].shift(1), mode='lines', name='Média Móvel')

    # Add lower and upper limit lines
    fig.add_scatter(x=df['DATA_PRECO'], y=df['LIMITE_INFERIOR'].shift(1), mode='lines', fill='tonexty', name='Limite Inferior')
    fig.add_scatter(x=df['DATA_PRECO'], y=df['LIMITE_SUPERIOR'].shift(1), mode='lines', fill='tonexty', name='Limite Superior')

    # Highlight prices outside the limit
    fig.add_scatter(x=df[df['dentro_limites'] == False]['DATA_PRECO'], y=df[df['dentro_limites'] == False]['PRECO'],
                    mode='markers', name='Preços Fora do Limite', marker=dict(color='red'))

    return fig

# Chamar a função para carregar e processar os dados
df = read_data(data_path / "CRITICA BP_PILOTO.csv")

# UI #
st.title("Críticas BP")

st.sidebar.title("Menu")
insumos_inf = df["INS_INF"].unique()
insumo_inf = st.sidebar.selectbox("Selecione um insumo:", insumos_inf, format_func=lambda x: x + " - " + df[df["INS_INF"] == x]["NM_INSUMO"].iloc[0])
desvios = st.sidebar.slider("Desvios Padrão",min_value=1.0,max_value=4.0,step=0.5,value=2.5)

# Processando os dados
df = process_data(df=df,n_desvios=desvios)

# Filtrando os dados
df = df[df["INS_INF"] == insumo_inf].reset_index(drop=True)

# Criando o gráfico
fig = plot(df)
st.plotly_chart(fig, use_container_width=True)

# Mostrando um indicador com total de preços um passo a frente dentro e fora do intervalo de confiança
total = len(df)
total_dentro = len(df[df['dentro_limites'] == True])
total_fora = len(df[df['dentro_limites'] == False])
st.write(f"Total de preços um passo a frente: {total}")
st.write(f"Total de preços um passo a frente dentro do intervalo de confiança: {total_dentro}")


st.write("### Preços que ficaram de fora da cerca")
st.write(df[df['dentro_limites'] == False].sort_values(by='DATA_PRECO', ascending=False).drop(['LIMITE_SUPERIOR', 'LIMITE_INFERIOR','MEDIANA_MOVEL','MEDIA_MOVEL','DESVIO_PADRAO'], axis=1))