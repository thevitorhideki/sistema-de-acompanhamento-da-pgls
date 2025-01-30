import streamlit as st

st.set_page_config(
    page_title="PGLS | Início",
    layout="wide",
    page_icon=":book:"
)

st.write("# Bem vindo ao Sistema de Acompanhamento da PGLS :wave:")
st.write("Aqui é possível acompanhar o desempenho dos professores e da turma de PGLS.")
st.write('---')
st.write("### Menu de Navegação")
st.write("1. **Acompanhamento de Docentes**")
st.write("Nessa aba é possível acompanhar o desempenho dos professores das disciplinas de PGLS. São apresentados dados valiosos para o acompanhamento do docente, como o plano de aula de cada disciplina, o feedback que recebeu de suas turmas e outros indicadores.")
st.write("2. **Acompanhamento de Turmas**")
st.write("Nessa aba é possível acompanhar o desempenho das turmas de PGLS. É ideal para entender como uma turma está indo em relação ao engajamento e satisfação com os professores e o curso.")
st.write('---')
st.write('### Sobre o Sistema')
st.write('Esse sistema foi desenvolvido para auxiliar a coordenação executiva de PGLS a acompanhar o desempenho dos professores e da turma.')
st.write('Como houve uma mudança no sistema de avaliação durante o ano de 2024, uma parte dos dados é estático e está em um arquivo CSV. A outra parte dos dados é dinâmico e consome o banco de dados do Insper.')
st.write('O repositorío do projeto pode ser encontrado [aqui](https://github.com/thevitorhideki/sistema-de-acompanhamento-da-pgls)')
st.write('---')
st.write('### Desenvolvedor')
st.write('Desenvolvido por [Vitor Hideki Pereira Katakura](https://github.com/thevitorhideki) durante o estágio de verão de 2025.01')
st.write('Para mais informações, entre em contato pelo email: thevitorhpk@gmail.com. Ou busque a equipe de PGLS')