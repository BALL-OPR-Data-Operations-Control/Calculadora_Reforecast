import streamlit as st
import pandas as pd

# exemplo de dados
df = pd.DataFrame({
    "Produto": ["A", "B", "C", "D", "E"],
    "Quantidade": [10, 0, 55, -2, 100]
})

st.subheader("Tabela de Input")
st.dataframe(df)

# inputs do usuário para condição
col1, col2 = st.columns(2)
coluna = col1.selectbox("Escolha a coluna para aplicar a regra:", df.columns)
condicao = col2.text_input("Digite a condição (ex: ==0, >50, <0)", "==0")

# função para aplicar cor
def color_dynamic(val):
    try:
        expr = str(val) + condicao
        if eval(expr):  # avalia a expressão
            return "background-color: rgba(0,255,0,0.2); color: #004d00;"  # verde suave
        else:
            return "background-color: rgba(255,0,0,0.2); color: #7a0000;"  # vermelho suave
    except:
        return ""

# aplica estilo somente na coluna escolhida
styled = df.style.applymap(color_dynamic, subset=[coluna])

st.subheader("Tabela de Output com Cores Dinâmicas")
st.dataframe(styled, use_container_width=True)
