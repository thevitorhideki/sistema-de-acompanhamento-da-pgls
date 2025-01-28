import streamlit as st
import pandas as pd
import sqlite3
import re
from openai import OpenAI

st.set_page_config(page_title="PGLS | Acompanhamento de Turmas",
                   page_icon="📈", layout='wide')

client = OpenAI()


def fetch_data():
    # Conecta ao banco de dados
    conn = sqlite3.connect(st.secrets['DATABASE_URL'])

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
        SELECT responseValue, responseZeroValue, surveyId, surveyAssessmentFactId, questionId, responseSetId, periodId, courseId, personAssesseeId FROM tb_course_evaluation_responseLikertFact
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

    surveyAssessmentFact_ids = responses['surveyAssessmentFactId'].unique()
    surveyAssessmentFact_ids_str = ', '.join(
        map(str, surveyAssessmentFact_ids))
    query = f"""
        SELECT surveyAssessmentFactId, totalExpectedSurveys, totalSurveysTaken, responseRate FROM tb_course_evaluation_surveyAssessmentFact
        WHERE surveyAssessmentFactId in ({surveyAssessmentFact_ids_str})
    """
    surveyAssessmentFact_dim = pd.read_sql_query(query, conn)

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

    return teachers, responses, surveys_dim, surveyAssessmentFact_dim, question_dim, response_set_dim, period_dim, course_dim, comments


def extrair_turma_e_divisao(codigo):
    # Expressão regular para extrair a turma (letras e números iniciais)
    match_turma = re.match(r'^[A-Za-z]+\d+', codigo)
    turma = match_turma.group(0) if match_turma else codigo

    # Expressão regular para extrair a divisão (últimos caracteres após "_", se existir)
    match_divisao = re.search(r'_(\w+)$', codigo)
    divisao = match_divisao.group(1) if match_divisao else None

    # Retorna a turma com a divisão anexada, se existir
    return f"{turma}_{divisao}" if divisao else turma


def group_responses(teachers, responses, surveys_dim, surveyAssessmentFact_dim, question_dim, response_set_dim, period_dim, course_dim):
    # Junta as respostas com os professores
    responses_joined_with_teachers = pd.merge(
        responses, teachers, left_on='personAssesseeId', right_on='personId')
    responses_joined_with_teachers.drop(
        columns=['personId', 'personAssesseeId'], inplace=True)

    # Junta as respostas com os nomes das pesquisas
    responses_joined_with_surveys = pd.merge(
        responses_joined_with_teachers, surveys_dim, on='surveyId')
    responses_joined_with_surveys.drop(columns=['surveyId'], inplace=True)

    # Junta as respostas com os dados das pesquisas
    responses_joined_with_surveys = pd.merge(
        responses_joined_with_surveys, surveyAssessmentFact_dim, on='surveyAssessmentFactId')
    responses_joined_with_surveys.drop(
        columns=['surveyAssessmentFactId'], inplace=True)

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
         'periodYear', 'courseName', 'courseNumber', 'schoolCourseCode', 'totalExpectedSurveys',
         'totalSurveysTaken', 'responseRate']).agg(
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
st.write("Este é um sistema de acompanhamento de turmas da PGLS. Aqui você conseguirá ver as disciplinas que os alunos dessas turmas cursaram, as suas avaliações sobre os professores e os comentários feitos por eles.")

# Busca os dados do banco e chama as funções responsáveis por modificar eles
teachers, responses, surveys_dim, surveyAssessmentFact_dim, question_dim, response_set_dim, period_dim, course_dim, comments = fetch_data()
responses_grouped = group_responses(
    teachers, responses, surveys_dim, surveyAssessmentFact_dim, question_dim, response_set_dim, period_dim, course_dim)
comments_grouped = group_comments(
    comments, responses_grouped['schoolCourseCode'].unique())
lesson_plans = pd.read_csv('src/data/lesson_plans.csv')

# Cria uma lista de anos disponíveis para filtrar
years_available = responses_grouped['year'].unique().tolist()
years_available.sort(reverse=True)
ano = st.multiselect('Selecione o ano', years_available,
                     default=years_available)

# Filtra os dados pelo ano
responses_grouped = responses_grouped[responses_grouped['year'].isin(ano)]

# Cria uma lista com os nomes dos professores para serem filtrados
turmas_list = responses_grouped['turma'].unique().tolist()

# Cria a caixa de seleção para filtrar os professores
turma = st.selectbox('Selecione a turma', [
    'Nenhuma'] + turmas_list)

# Cria a caixa de seleção para filtrar as turmas
if turma == 'Nenhuma':
    professor = st.selectbox('Selecione o professor', ['Todos'], disabled=True)
else:
    professor = st.selectbox('Selecione o professor', [
        'Todos'] + responses_grouped[responses_grouped['turma'] == turma]['fullName'].unique().tolist())

if professor == 'Todos':
    dados_filtrados = responses_grouped.copy()
    fitered_comments = comments_grouped[comments_grouped['turma'] == turma]
else:
    dados_filtrados = responses_grouped[responses_grouped['fullName'] == professor].copy(
    )

if turma != 'Nenhuma':
    # Filtra os dados pela turma
    dados_filtrados = dados_filtrados[dados_filtrados['turma'] == turma]
    dados_filtrados = pd.merge(
        dados_filtrados, lesson_plans, left_on='classCode', right_on='codigo_turma', how='left')

    # Mostra as disciplinas que a turma teve
    st.write("## Disciplinas que a turma teve:")
    for index, row in dados_filtrados.drop_duplicates('classCode').iterrows():
        st.write(f"#### Disciplina: {row['courseName']}")
        col1, col2, col3 = st.columns(3, vertical_alignment='center')
        with col1:
            st.metric(label="Ano", value=row['year'])
        with col2:
            st.metric(label="Período", value=row['period'])
        with col3:
            if pd.isna(row['link']):
                st.metric(label="Plano de aula", value="Não disponível")
            else:
                st.page_link(row['link'], label="Plano de aula")
        st.metric(label="Professores", value=row['professores'])
        st.markdown("---")

    # Agrupa as notas por categoria e faz a média das notas
    feedbacks = dados_filtrados.groupby(['questionSubCategory', 'year', 'period', 'responseScale', 'classCode', 'turma',
                                         'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate']).agg({
                                             'responseValue': 'mean'
                                         })

    st.write('## Avaliações por categoria')
    df_feedbacks = feedbacks.reset_index()
    df_feedbacks = df_feedbacks[df_feedbacks['responseRate'] > 30]

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

    # Cria um checkbox para cada disciplina para mostrar ou não as notas
    class_codes = df_feedbacks['classCode'].unique().tolist()
    classes_to_show = st.pills("Selecione as turmas para visualizar as notas",
                               class_codes, selection_mode="multi", default=class_codes)

    df_feedbacks = df_feedbacks[df_feedbacks['classCode'].isin(
        classes_to_show)]

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

    # Total de respostas por disciplina
    survey_info_grouped = (df_feedbacks.groupby(['classCode'])[[
        'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate']].max())

    for index, row in survey_info_grouped.iterrows():
        st.write(f"### Disciplina: {index}")
        col1, col2, col3, = st.columns(3)
        with col1:
            st.metric(label="Total de respostas esperadas",
                      value=row['totalExpectedSurveys'])
        with col2:
            st.metric(label="Total de respostas recebidas",
                      value=row['totalSurveysTaken'])
        with col3:
            st.metric(label="Taxa de resposta", value=row['responseRate'])
        st.markdown("---")

    st.write("## Comentários")

    # Pega todos os comentários de um professor
    continue_doing = 'Continue fazendo: '
    stop_doing = 'Pare de fazer: '
    start_doing = 'Comece a fazer: '
    all_comments = []

    for index, row in fitered_comments.iterrows():
        continue_doing += ' '.join(row['continue_doing_comments'])
        stop_doing += ' '.join(row['stop_doing_comments'])
        start_doing += ' '.join(row['start_doing_comments'])

    # Faz um resumo dos comentários com o GPT-4o-mini
    if st.button("Gerar resumo dos comentários"):
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "developer", "content": "A seguir, há uma lista de comentários de alunos sobre o professor. Escreva um resumo deles e sugira melhorias."},
                {"role": "user", "content": continue_doing + stop_doing + start_doing},
            ]
        )

        st.write(response.choices[0].message.content)
    st.write('---')
    # Mostra os comentários
    for index, row in fitered_comments.iterrows():
        st.write(f"Professor: {row['eval_username']}")
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
