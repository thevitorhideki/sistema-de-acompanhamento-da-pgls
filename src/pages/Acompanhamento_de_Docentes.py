import streamlit as st
import pandas as pd
import sqlite3
import re
from openai import OpenAI

# Configurações da página
st.set_page_config(
    page_title="PGLS | Acompanhamento de Docentes", page_icon="📈", layout='wide')

# Inicializa o client da OpenAI
client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)


def fetch_data():
    # Conecta ao banco de dados
    conn = sqlite3.connect(st.secrets.DATABASE_URL)

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

    # Pega os ids únicos para buscar na tabela de informações das pesquisas
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


def extract_class_and_subdivision(code):
    # Expressão regular para extrair a turma (letras e números iniciais)
    match_class = re.match(r'^[A-Za-z]+\d+', code)
    class_code = match_class.group(0) if match_class else code

    # Expressão regular para extrair a divisão (últimos caracteres após "_", se existir)
    match_subdivision = re.search(r'_(\w+)$', code)
    subdivision = match_subdivision.group(1) if match_subdivision else None

    # Retorna a turma com a divisão anexada, se existir
    return f"{class_code}_{subdivision}" if subdivision else class_code


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

    # Renomeia as colunas
    responses_from_pgls = responses_from_pgls.rename(columns={
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
    })

    # Converte o ano para inteiro
    responses_from_pgls['year'] = responses_from_pgls['year'].apply(int)

    # Adiciona uma coluna "turma" com a turma e a divisão
    responses_from_pgls.loc[:, 'classCode'] = responses_from_pgls['schoolCourseCode'].apply(
        lambda x: x.split('.')[-1])
    responses_from_pgls.loc[:, 'turma'] = responses_from_pgls['classCode'].apply(
        extract_class_and_subdivision)
    responses_from_pgls.loc[:, 'fullName'] = responses_from_pgls['fullName'].apply(
        lambda x: x.upper())

    # Agrupa as notas por professor, curso e pesquisa
    responses_grouped = responses_from_pgls.groupby(
        ['departmentName', 'classCode', 'turma', 'fullName', 'lastNameFirst', 'teacher', 'email', 'survey',
         'question', 'questionSubCategory', 'responseScale', 'responseLegend', 'period',
         'year', 'courseName', 'courseNumber', 'schoolCourseCode', 'totalExpectedSurveys',
         'totalSurveysTaken', 'responseRate']).agg(
        {'responseZeroValue': 'mean', 'responseValue': 'mean'}).reset_index()

    # Ordena os dados
    responses_grouped.sort_values(
        by=['year', 'schoolCourseCode', 'teacher'], inplace=True)

    # Reseta o índice
    responses_grouped.reset_index(drop=True, inplace=True)

    nps_teachers = responses_from_pgls[responses_from_pgls['questionSubCategory']
                                       == 'Avaliação Geral']
    nps_teachers = nps_teachers.groupby(['fullName', 'email', 'classCode', 'survey', 'period', 'totalExpectedSurveys',
                                         'totalSurveysTaken', 'responseRate'])['responseValue'].apply(lambda x: x.dropna().tolist()).reset_index()
    nps_teachers.rename(columns={'responseValue': 'nps_index'}, inplace=True)
    nps_teachers['nps_index'] = nps_teachers['nps_index'].apply(tuple)
    nps_teachers.drop_duplicates(inplace=True)

    promoters_count = (nps_teachers.explode('nps_index')
                       .groupby(['email', 'fullName', 'classCode', 'survey', 'period',
                                 'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate'])
                       .agg(count=('nps_index', lambda x: (x >= 9).sum()))
                       .reset_index())

    detractors_count = (nps_teachers.explode('nps_index')
                        .groupby(['email', 'fullName', 'classCode', 'survey', 'period',
                                  'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate'])
                        .agg(count=('nps_index', lambda x: (x <= 7).sum()))
                        .reset_index())

    total = (nps_teachers.explode('nps_index')
             .groupby(['email', 'fullName', 'classCode', 'survey', 'period',
                       'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate'])
             .agg(count=('nps_index', 'count'))
             .reset_index())

    joined_nps = pd.merge(promoters_count, detractors_count, on=['email', 'fullName', 'classCode', 'survey', 'period', 'totalExpectedSurveys',
                                                                 'totalSurveysTaken', 'responseRate'])
    joined_nps = pd.merge(joined_nps, total, on=['email', 'fullName', 'classCode', 'survey', 'period', 'totalExpectedSurveys',
                                                 'totalSurveysTaken', 'responseRate'])

    joined_nps.columns = ['email', 'fullName', 'classCode', 'survey', 'period', 'totalExpectedSurveys',
                          'totalSurveysTaken', 'responseRate', 'PROMOTERS', 'DETRACTORS', 'TOTAL']

    joined_nps['NPS'] = ((joined_nps['PROMOTERS'] -
                         joined_nps['DETRACTORS']) / joined_nps['TOTAL']) * 100

    return responses_grouped, joined_nps


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

    # Cria uma coluna com a turma
    comments_grouped['turma'] = comments_grouped['crs_code'].apply(
        lambda x: x.split('.')[-1]).apply(extract_class_and_subdivision)

    # Limpa os comentários
    comments_grouped['continue_doing_comments'] = comments_grouped['continue_doing_comments'].apply(
        clear_comments)
    comments_grouped['stop_doing_comments'] = comments_grouped['stop_doing_comments'].apply(
        clear_comments)
    comments_grouped['start_doing_comments'] = comments_grouped['start_doing_comments'].apply(
        clear_comments)

    return comments_grouped


# Configurações da página
st.title("Sistema de acompanhamento de docentes")
st.write("Nessa aba é possível acompanhar o desempenho dos professores das disciplinas de PGLS. São apresentados dados valiosos para o acompanhamento do docente, como o plano de aula de cada disciplina, o feedback que recebeu de suas turmas e outros indicadores.")

# Busca os dados do banco e chama as funções responsáveis por modificar eles
teachers, responses, surveys_dim, surveyAssessmentFact_dim, question_dim, response_set_dim, period_dim, course_dim, comments = fetch_data()
responses_grouped, nps = group_responses(
    teachers, responses, surveys_dim, surveyAssessmentFact_dim, question_dim, response_set_dim, period_dim, course_dim)
comments_grouped = group_comments(
    comments, responses_grouped['schoolCourseCode'].unique())
lesson_plans = pd.read_csv('data/lesson_plans.csv')
old_survey_parcial = pd.read_csv('data/old_pgls_parcial.csv')
old_survey_final = pd.read_csv('data/old_pgls_final.csv')

# Cria uma lista de anos disponíveis para filtrar
years_available = responses_grouped['year'].unique().tolist()
years_available.sort(reverse=True)
year = st.multiselect('Selecione o ano', years_available,
                      default=years_available)

# Filtra os dados pelo ano
responses_grouped = responses_grouped[responses_grouped['year'].isin(year)]
# old_survey_final = old_survey_final[old_survey_final['ano'].isin(year)]
# old_survey_parcial = old_survey_parcial[old_survey_parcial['ano'].isin(year)]

# Cria uma lista com os nomes dos professores para serem filtrados
teachers_names = [name.upper()
                  for name in responses_grouped['fullName'].unique().tolist()]
# teachers_names = list(set(old_survey_parcial['professor'].unique().tolist(
# ) + old_survey_final['professor'].unique().tolist() + teachers_names))
teachers_names = sorted(teachers_names)

# Cria a caixa de seleção para filtrar os professores
teacher = st.selectbox('Selecione o Professor', [
    'Nenhum'] + teachers_names)

# Cria a caixa de seleção para filtrar as turmas
if teacher == 'Nenhum':
    class_codes_list = list(set(responses_grouped['turma'].unique().tolist(
    ) + old_survey_final['turma'].unique().tolist() + old_survey_parcial['turma'].unique().tolist()))
    class_code = st.selectbox('Selecione a turma', [
        'Todas'] + class_codes_list, disabled=True)
else:
    class_codes_list = responses_grouped[responses_grouped['fullName']
                                         == teacher]['turma'].unique().tolist() + old_survey_final[old_survey_final['professor'] == teacher]['turma'].unique().tolist() + old_survey_parcial[old_survey_parcial['professor'] == teacher]['turma'].unique().tolist()
    class_code = st.selectbox('Selecione a turma', [
                              'Todas'] + class_codes_list)
class_codes_list.sort()

# Copia o dataframe original para filtrar. Se a turma for 'Todas', não filtra, senão filtra pela turma
if class_code == 'Todas':
    filtered_data = responses_grouped.copy()
else:
    filtered_data = responses_grouped[responses_grouped['turma'] == class_code].copy(
    )
    comments_grouped = comments_grouped[comments_grouped['turma'] == class_code]

if teacher != 'Nenhum':
    # Filtra os dados pelo professor
    filtered_data = filtered_data[filtered_data['fullName'] == teacher]
    filtered_data = pd.merge(
        filtered_data, lesson_plans, left_on='classCode', right_on='codigo_turma', how='left')
    nps = nps[nps['fullName'] == teacher]

    # Mostra as disciplinas que o professor ministrou
    st.write("## Disciplinas que esse professor ministrou:")
    for index, row in filtered_data.drop_duplicates('classCode').iterrows():
        st.write(f"#### Disciplina: {
                 row['courseName']} - Turma: {row['turma']}")
        col1, col2, col3, = st.columns(3, vertical_alignment='center')
        with col1:
            st.metric(label="Ano", value=row['year'])
        with col2:
            st.metric(label="Período", value=row['period'])
        with col3:
            if pd.isna(row['link']):
                st.metric(label="Plano de aula", value="Não disponível")
            else:
                st.page_link(row['link'], label="Plano de aula")
        st.markdown("---")
    # Agrupa as notas por categoria e faz a média das notas
    feedbacks = filtered_data.groupby(['questionSubCategory', 'year', 'period', 'responseScale', 'classCode', 'turma',
                                       'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate', 'courseName']).agg({
                                           'responseValue': 'mean'
                                       })

    st.write('## Avaliações por categoria')
    df_feedbacks = feedbacks.reset_index()

    min_responses_relative = st.slider(
        "Quantidade relativa de respostas", 0, 100, 20)
    # Busca as turmas que tiveram uma taxa de resposta acima de um valor mínimo
    df_feedbacks = df_feedbacks[df_feedbacks['responseRate']
                                > min_responses_relative]

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
        height=600
    )

    # Total de respostas por disciplina
    survey_info_grouped = (df_feedbacks.groupby(['classCode', 'courseName'])[[
        'classCode', 'totalExpectedSurveys', 'totalSurveysTaken', 'responseRate']].max())

    for index, row in survey_info_grouped.iterrows():
        st.write(f"### Disciplina: {index[1]}")
        col1, col2, col3, = st.columns(3)
        with col1:
            st.metric(label="Total de respostas esperadas",
                      value=row['totalExpectedSurveys'])
            st.metric(label="Promotores",
                      value=nps[nps['classCode'] == index[0]]['PROMOTERS'].values[0])
        with col2:
            st.metric(label="Total de respostas recebidas",
                      value=row['totalSurveysTaken'])
            st.metric(label="Detratores",
                      value=nps[nps['classCode'] == index[0]]['DETRACTORS'].values[0])
        with col3:
            st.metric(label="Taxa de resposta", value=f"{row['responseRate']}%")
            st.metric(
                label="NPS", value=nps[nps['classCode'] == index[0]]['NPS'].values[0])
        st.markdown("---")

    st.write("## Comentários")

    # Acha o username do professor
    teachers_username = teachers[teachers['fullName'].str.upper(
    ) == teacher]['coursevalUserName'].values[0]

    # Filtra os comentários do professor
    comments_teacher = comments_grouped[(
        comments_grouped['eval_username'] == teachers_username)]

    # Pega todos os comentários de um professor
    continue_doing = 'Continue fazendo: '
    stop_doing = 'Pare de fazer: '
    start_doing = 'Comece a fazer: '
    all_comments = []

    for index, row in comments_teacher.iterrows():
        continue_doing += ' '.join(row['continue_doing_comments'])
        stop_doing += ' '.join(row['stop_doing_comments'])
        start_doing += ' '.join(row['start_doing_comments'])

    # Faz um resumo dos comentários com o GPT-4o-mini
    if st.button("Gerar resumo dos comentários"):
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "developer", "content": st.secrets.TEACHER_PROMPT},
                {"role": "user", "content": continue_doing + stop_doing + start_doing},
            ]
        )

        st.write(response.choices[0].message.content)
    st.write('---')
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
