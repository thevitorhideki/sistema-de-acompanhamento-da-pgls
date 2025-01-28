import streamlit as st

st.set_page_config(
    page_title="PGLS | Início",
    layout="wide",
    page_icon=":book:"
)

st.write("# Bem vindo ao Sistema de Gerenciamento da PGLS :wave:")
st.write("Nesse sistema é possível acompanhar o desempenho dos professores e da turma de PGLS.")
st.write('---')
st.write("### Menu de Navegação")
st.write("1. **Avaliação dos Professores**")
st.write("Nessa aba é possível acompanhar o desempenho dos professores da disciplina de PGLS. São apresentados gráficos com a média dos feedbacks e comentários dos alunos.")
st.write("2. **Avaliação da Turma**")
st.write("Nessa aba é possível acompanhar o desempenho da turma de PGLS. São apresentados gráficos com a média dos feedbacks e comentários da turma.")
