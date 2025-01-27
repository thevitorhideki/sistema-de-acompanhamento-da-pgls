import streamlit as st
import pandas as pd
import sqlite3
import re
import os
from dotenv import load_dotenv

st.set_page_config(
    page_title="PGLS | Acompanhamento de Docentes", page_icon="📈", layout='wide')

# Carrega as variáveis ambiente
load_dotenv()


def fetch_data():
    # Conecta ao banco de dados
    conn = sqlite3.connect(os.getenv('DATABASE_URL'))

    # Busca todos os campos da tabela de pessoas onde ela está ativa na escola, é um professor e o nome do programa é Not Applicable
    query = """
        SELECT departmentName, personId, fullName, lastNameFirst, coursevalUserName, email FROM tb_course_evaluation_personDim
        WHERE personStatus == 'Active'
        AND facultyYn == 'Y'
    """

    # Executa a query e coloca o resultado em um DataFrame
    teachers = pd.read_sql_query(query, conn)

    # Pega os ids dos professores
    teachers_ids = teachers['personId'].unique()
    # Coloca os ids em uma só string separado por vírgulas
    teachers_ids_str = ', '.join(map(str, teachers_ids))

    # Busca pelas respostas as quais remetem aos professores da PGLS
    query = f"""
        SELECT responseValue, responseZeroValue, surveyId, questionId, responseSetId, periodId, courseId, personAssesseeId FROM tb_course_evaluation_responseLikertFact
        WHERE personAssesseeId IN ({teachers_ids_str})
    """
    responses = pd.read_sql_query(query, conn)

    # Pega os ids únicos para buscar na tabela de pesquisas
    surveys_ids = responses['surveyId'].unique()
    surveys_ids_str = ', '.join(map(str, surveys_ids))
    query = f"""
        SELECT surveyId, surveyName FROM tb_course_evaluation_surveyDim
        WHERE surveyId in ({surveys_ids_str})
    """
    surveys_dim = pd.read_sql_query(query, conn)

    # Pega os ids únicos para buscar na tabela de perguntas
    questions_ids = responses['questionId'].sort_values().unique()
    questions_ids_str = ', '.join(map(str, questions_ids))
    query = f"""
        SELECT questionId, question, questionSubCategory FROM tb_course_evaluation_questionDim
        WHERE questionId in ({questions_ids_str})
    """
    question_dim = pd.read_sql_query(query, conn)

    # Pega os ids únicos para buscar na tabela de respostas
    responseSet_ids = responses['responseSetId'].unique()
    responseSet_ids_str = ', '.join(map(str, responseSet_ids))
    query = f"""
        SELECT responseScale, responseSetId, responseValue, responseLegend FROM tb_course_evaluation_responseSetDim
        WHERE responseSetId in ({responseSet_ids_str})
    """
    response_set_dim = pd.read_sql_query(query, conn)

    # Pega os ids únicos para buscar na tabela de períodos
    periods_ids = responses['periodId'].unique()
    periods_ids_str = ', '.join(map(str, periods_ids))
    query = f"""
        SELECT periodId, periodName, periodYear FROM tb_course_evaluation_periodDim
        WHERE periodId in ({periods_ids_str})
    """
    period_dim = pd.read_sql_query(query, conn)

    # Pega os ids únicos para buscar na tabela de cursos
    courses_ids = responses['courseId'].unique()
    courses_ids_str = ', '.join(map(str, courses_ids))
    query = f"""
        SELECT courseId, courseName, courseNumber, schoolCourseCode FROM tb_course_evaluation_courseDim
        WHERE courseId in ({courses_ids_str})
    """
    course_dim = pd.read_sql_query(query, conn)

    # Busca os comentários
    query = f"""
        SELECT crs_code, eval_username, question, survey, response FROM tb_course_evaluation_results_Comments
    """
    comments = pd.read_sql_query(query, conn)

    # Fecha a conexão com o banco de dados
    conn.close()

    return teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim, comments


def extrair_turma_e_divisao(codigo):
    # Expressão regular para extrair a turma (letras e números iniciais)
    match_turma = re.match(r'^[A-Za-z]+\d+', codigo)
    turma = match_turma.group(0) if match_turma else codigo

    # Expressão regular para extrair a divisão (últimos caracteres após "_", se existir)
    match_divisao = re.search(r'_(\w+)$', codigo)
    divisao = match_divisao.group(1) if match_divisao else None

    # Retorna a turma com a divisão anexada, se existir
    return f"{turma}_{divisao}" if divisao else turma


def group_responses(teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim):
    # Junta as respostas com os professores
    responses_joined_with_teachers = pd.merge(
        responses, teachers, left_on='personAssesseeId', right_on='personId')
    responses_joined_with_teachers.drop(
        columns=['personId', 'personAssesseeId'], inplace=True)

    # Junta as respostas com os nomes das pesquisas
    responses_joined_with_surveys = pd.merge(
        responses_joined_with_teachers, surveys_dim, on='surveyId')
    responses_joined_with_surveys.drop(columns=['surveyId'], inplace=True)

    # Junta as perguntas às respostas
    responses_joined_with_questions = pd.merge(
        responses_joined_with_surveys, question_dim, on='questionId')
    responses_joined_with_questions.drop(columns=['questionId'], inplace=True)

    responses_joined_with_questions = pd.merge(
        responses_joined_with_questions, response_set_dim, on=['responseSetId', 'responseValue'])
    responses_joined_with_questions.drop(
        columns=['responseSetId'], inplace=True)

    # Junta os períodos às respostas
    responses_joined_with_periods = pd.merge(
        responses_joined_with_questions, period_dim, on='periodId')
    responses_joined_with_periods.drop(columns=['periodId'], inplace=True)

    # Junta os cursos às respostas
    responses_joined_with_courses = pd.merge(
        responses_joined_with_periods, course_dim, on='courseId')
    responses_joined_with_courses.drop(columns=['courseId'], inplace=True)

    responses_from_pgls = responses_joined_with_courses[responses_joined_with_courses['surveyName'].str.contains(
        'PGLS')]

    # Agrupa as notas por professor, curso e pesquisa
    responses_grouped = responses_from_pgls.groupby(
        ['departmentName', 'fullName', 'lastNameFirst', 'coursevalUserName', 'email', 'surveyName',
         'question', 'questionSubCategory', 'responseScale', 'responseLegend', 'periodName',
         'periodYear', 'courseName', 'courseNumber', 'schoolCourseCode']).agg(
        {'responseZeroValue': 'mean', 'responseValue': 'mean'}).reset_index()

    # Renomeia as colunas
    responses_grouped.rename(columns={
        'coursevalUserName': 'teacher',
        'schoolCourseCode': 'schoolCourseCode',
        'surveyName': 'survey',
        'question': 'question',
        'questionSubCategory': 'questionSubCategory',
        'responseScale': 'responseScale',
        'responseLegend': 'responseLegend',
        'periodName': 'period',
        'periodYear': 'year',
        'courseName': 'courseName',
        'courseNumber': 'courseNumber',
        'responseZeroValue': 'responseZeroValue',
        'responseValue': 'responseValue'
    }, inplace=True)

    # Converte o ano para inteiro
    responses_grouped['year'] = responses_grouped['year'].apply(int)

    # Adiciona uma coluna "turma" com a turma e a divisão
    responses_grouped['classCode'] = responses_grouped['schoolCourseCode'].apply(
        lambda x: x.split('.')[-1])
    responses_grouped['turma'] = responses_grouped['classCode'].apply(
        extrair_turma_e_divisao)
    responses_grouped['fullName'] = responses_grouped['fullName'].apply(
        lambda x: x.upper())

    # Ordena os dados
    responses_grouped.sort_values(
        by=['year', 'schoolCourseCode', 'teacher'], inplace=True)

    # Reseta o índice
    responses_grouped.reset_index(drop=True, inplace=True)

    return responses_grouped


def clear_comments(comments: tuple[str]):
    comments_formatted = []
    for comment in comments:
        if len(comment) > 5:
            comments_formatted.append(comment)

    return comments_formatted


def group_comments(comments, schoolCourseCodes):
    # Substitui os valores das perguntas por valores mais legíveis
    comments['question'] = comments['question'].replace({
        'O professor continue a fazer em sala de aula. / What should the professor continue doing in this course?': 'continue_doing',
        'O professor deixe de fazer em sala de aula. / What should the professor stop doing in the classroom?': 'stop_doing',
        'O professor passe a fazer em sala de aula. / What should the professor start doing in the classroom?': 'start_doing'
    })

    # Filtra os comentários que possuem as perguntas de interesse e os códigos de curso da PGLS
    comments = comments[(comments['question'].isin(['continue_doing', 'stop_doing', 'start_doing'])) & (
        comments['crs_code'].isin(schoolCourseCodes))]

    # Agrupa os comentários por codigo da turma, professor, pesquisa e pergunta
    comments_grouped = comments.groupby(['crs_code', 'eval_username', 'survey', 'question'])[
        'response'].apply(lambda x: x.dropna().tolist()).reset_index()

    # Cria uma coluna para cada tipo resposta
    comments_grouped = comments_grouped.pivot_table(
        index=['crs_code', 'eval_username', 'survey'], columns='question', values='response', aggfunc='first').reset_index()

    # Retira o nome das colunas
    comments_grouped.columns.name = None

    # Renomeia as colunas
    comments_grouped.rename(columns={
        'continue_doing': 'continue_doing_comments',
        'stop_doing': 'stop_doing_comments',
        'start_doing': 'start_doing_comments'
    }, inplace=True)

    # Preenche os valores nulos com uma string vazia
    comments_grouped.fillna('', inplace=True)

    # Transforma as listas de comentários em tuplas
    comments_grouped['continue_doing_comments'] = comments_grouped['continue_doing_comments'].apply(
        tuple)
    comments_grouped['stop_doing_comments'] = comments_grouped['stop_doing_comments'].apply(
        tuple)
    comments_grouped['start_doing_comments'] = comments_grouped['start_doing_comments'].apply(
        tuple)

    comments_grouped['turma'] = comments_grouped['crs_code'].apply(
        lambda x: x.split('.')[-1]).apply(extrair_turma_e_divisao)

    comments_grouped['continue_doing_comments'] = comments_grouped['continue_doing_comments'].apply(
        clear_comments)
    comments_grouped['stop_doing_comments'] = comments_grouped['stop_doing_comments'].apply(
        clear_comments)
    comments_grouped['start_doing_comments'] = comments_grouped['start_doing_comments'].apply(
        clear_comments)

    return comments_grouped


# Configurações da página
st.title("Sistema de acompanhamento de docentes")
st.write("Este é um sistema de acompanhamento de docentes da PGLS. Aqui você pode ver os feedbacks dos alunos sobre os professores.")

# Busca os dados do banco e chama as funções responsáveis por modificar eles
teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim, comments = fetch_data()
responses_grouped = group_responses(
    teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim)
comments_grouped = group_comments(
    comments, responses_grouped['schoolCourseCode'].unique())


# Cria uma lista de anos disponíveis para filtrar
years_available = responses_grouped['year'].unique().tolist()
years_available.sort(reverse=True)
ano = st.multiselect('Selecione o ano', years_available,
                     default=years_available)

# Filtra os dados pelo ano
responses_grouped = responses_grouped[responses_grouped['year'].isin(ano)]

# Cria uma lista com os nomes dos professores para serem filtrados
teachers_names = sorted(
    [name.upper() for name in responses_grouped['fullName'].unique().tolist()])

# Cria a caixa de seleção para filtrar os professores
professor = st.selectbox('Selecione o Professor', [
    'Todos'] + teachers_names)

# Cria a caixa de seleção para filtrar as turmas
if professor == 'Todos':
    turmas_list = responses_grouped['turma'].unique().tolist()
    turma = st.selectbox('Selecione a turma', [
                         'Todos'] + turmas_list, disabled=True)
else:
    turmas_list = responses_grouped[responses_grouped['fullName']
                                    == professor]['turma'].unique().tolist()
    turma = st.selectbox('Selecione a turma', ['Todos'] + turmas_list)
turmas_list.sort()

# Copia o dataframe original para filtrar. Se a turma for 'Todos', não filtra, senão filtra pela turma
if turma == 'Todos':
    dados_filtrados = responses_grouped.copy()
else:
    dados_filtrados = responses_grouped[responses_grouped['turma'] == turma].copy(
    )
    comments_grouped = comments_grouped[comments_grouped['turma'] == turma]

if professor != 'Todos':
    # Filtra os dados pelo professor
    dados_filtrados = dados_filtrados[dados_filtrados['fullName'] == professor]

    # Mostra as disciplinas que o professor ministrou
    st.write("Disciplinas que esse professor ministrou:")
    st.write(
        dados_filtrados[['year', 'courseName', 'turma']].drop_duplicates())

    # Agrupa as notas por categoria e faz a média das notas
    feedbacks = dados_filtrados.groupby(['questionSubCategory', 'year', 'period', 'responseScale', 'classCode', 'turma']).agg({
        'responseValue': 'mean'
    })

    st.write('## Avaliações por categoria (cada cor é uma disciplina)')
    df_feedbacks = feedbacks.reset_index()

    # Renomeia os valores das categorias para facilitar a visualização
    df_feedbacks['questionSubCategory'] = df_feedbacks['questionSubCategory'].replace({
        'Questões relacionadas ao feedback / Feedback:': 'feedback',
        'Questões relacionadas ao planejamento: / Course Planning and Structure:': 'planejamento',
        'Questões relacionadas à avaliação / Assessment:': 'avaliacao',
        'Questões relacionadas à dinâmica: / Classroom Dynamics:': 'dinamica',
    })

    # Cria uma coluna com o ano e o período
    df_feedbacks['yearAndPeriod'] = df_feedbacks['year'].astype(
        str) + '.' + df_feedbacks['period']

    # Filtra as categorias que não são de avaliação geral
    df_feedbacks = df_feedbacks[df_feedbacks['questionSubCategory']
                                != 'Avaliação Geral']

    # Plota o gráfico, com a categoria no eixo x, a nota no eixo y e a cor representando a turma
    st.line_chart(
        df_feedbacks,
        x='questionSubCategory',
        x_label="Categoria",
        y='responseValue',
        y_label="Valor",
        color='classCode',
        use_container_width=False,
        width=1300,
        height=600
    )

    st.write("## Comentários")
    # Acha o username do professor
    teachers_username = teachers[teachers['fullName'].str.upper(
    ) == professor]['coursevalUserName'].values[0]

    # Filtra os comentários do professor
    comments_teacher = comments_grouped[(
        comments_grouped['eval_username'] == teachers_username)]

    # Mostra os comentários
    for index, row in comments_teacher.iterrows():
        st.write(f"Turma: {row['turma']}")
        st.write(f"Comentários de {row['survey']}:")

        st.write(f"### O que o professor deve continuar fazendo:")
        for comment in row['continue_doing_comments']:
            st.write(f"- {comment}")

        st.write(f"### O que o professor deve parar de fazer:")
        for comment in row['stop_doing_comments']:
            st.write(f"- {comment}")

        st.write(f"### O que o professor deve começar a fazer:")
        for comment in row['start_doing_comments']:
            st.write(f"- {comment}")
        st.markdown("---")
