import streamlit as st
import pandas as pd
import sqlite3
import re
import os
from dotenv import load_dotenv

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
        AND programName == 'Not Applicable'
    """

    # Executa a query e coloca o resultado em um DataFrame
    teachers = pd.read_sql_query(query, conn)

    # Retira or cursos que não são da PGLS (Obtidos manualmente da coluna departmentName no qual o programName é Not Applicable)
    excluded_departments = [
        'ADMINISTRAÇÃO', 'DIREITO', 'DOUTORADO EM ECONOMIA DOS NEGÓCIOS',
        'MESTRADO PROFISSIONAL EM ADMINISTRAÇÃO', 'CIÊNCIAS ECONÔMICAS', 'Default',
        'MESTRADO PROFISSIONAL EM ECONOMIA', 'MESTRADO PROFISSIONAL EM POLÍTICAS PÚBLICAS',
        'DOUTORADO PROFISSIONAL EM ADMINISTRAÇÃO','EEBSPGCPJ', 'EEPCDBB', 'EEPCFSRS', 'EEPCGRHJL',
        'EEPCLAMN', 'EEPCLIAA', 'EEPCPPPD', 'CIÊNCIA DA COMPUTAÇÃO', 'ENGENHARIA DE COMPUTAÇÃO'
    ]

    # Retira os professores que não fazem parte dos programas da lista acima
    filtered_teachers = teachers[~teachers['departmentName'].isin(excluded_departments)]

    # Pega os ids dos professores
    teachers_ids = filtered_teachers['personId'].unique()
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
    
    return filtered_teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim, comments

def extrair_turma_e_divisao(codigo):
        # Expressão regular para extrair a turma (letras e números iniciais)
        match_turma = re.match(r'^[A-Za-z]+\d+', codigo)
        turma = match_turma.group(0) if match_turma else codigo

        # Expressão regular para extrair a divisão (últimos caracteres após "_", se existir)
        match_divisao = re.search(r'_(\w+)$', codigo)
        divisao = match_divisao.group(1) if match_divisao else None

        # Retorna a turma com a divisão anexada, se existir
        return f"{turma}_{divisao}" if divisao else turma

def group_responses(filtered_teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim):
    # Junta as respostas com os professores
    responses_joined_with_teachers = pd.merge(responses, filtered_teachers, left_on='personAssesseeId', right_on='personId')
    responses_joined_with_teachers.drop(columns=['personId', 'personAssesseeId'], inplace=True)

    # Junta as respostas com os nomes das pesquisas
    responses_joined_with_surveys = pd.merge(responses_joined_with_teachers, surveys_dim, on='surveyId')
    responses_joined_with_surveys.drop(columns=['surveyId'], inplace=True)

    # Junta as perguntas às respostas
    responses_joined_with_questions = pd.merge(responses_joined_with_surveys, question_dim, on='questionId')
    responses_joined_with_questions.drop(columns=['questionId'], inplace=True)

    responses_joined_with_questions = pd.merge(responses_joined_with_questions, response_set_dim, on=['responseSetId', 'responseValue'])
    responses_joined_with_questions.drop(columns=['responseSetId'], inplace=True)

    # Junta os períodos às respostas
    responses_joined_with_periods = pd.merge(responses_joined_with_questions, period_dim, on='periodId')
    responses_joined_with_periods.drop(columns=['periodId'], inplace=True)

    # Junta os cursos às respostas
    responses_joined_with_courses = pd.merge(responses_joined_with_periods, course_dim, on='courseId')
    responses_joined_with_courses.drop(columns=['courseId'], inplace=True)

    # Agrupa as notas por professor, curso e pesquisa
    responses_grouped = responses_joined_with_courses.groupby(
        ['departmentName', 'fullName', 'lastNameFirst', 'coursevalUserName', 'email', 'surveyName',
        'question','questionSubCategory', 'responseScale', 'responseLegend', 'periodName',
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
    responses_grouped['turma'] = responses_grouped['schoolCourseCode'].apply(lambda x: x.split('.')[-1]).apply(extrair_turma_e_divisao)
    responses_grouped['fullName'] = responses_grouped['fullName'].apply(lambda x: x.upper())

    # Ordena os dados
    responses_grouped.sort_values(by=['year', 'schoolCourseCode', 'teacher'], inplace=True)
    
    # Reseta o índice
    responses_grouped.reset_index(drop=True, inplace=True)
    
    return responses_grouped

def group_comments(comments, schoolCourseCodes):
    # Substitui os valores das perguntas por valores mais legíveis
    comments['question'] = comments['question'].replace({
        'O professor continue a fazer em sala de aula. / What should the professor continue doing in this course?': 'continue_doing',
        'O professor deixe de fazer em sala de aula. / What should the professor stop doing in the classroom?': 'stop_doing',
        'O professor passe a fazer em sala de aula. / What should the professor start doing in the classroom?': 'start_doing'
    })

    # Filtra os comentários que possuem as perguntas de interesse e os códigos de curso da PGLS
    comments = comments[(comments['question'].isin(['continue_doing', 'stop_doing', 'start_doing'])) & (comments['crs_code'].isin(schoolCourseCodes))]

    # Agrupa os comentários por codigo da turma, professor, pesquisa e pergunta
    comments_grouped = comments.groupby(['crs_code', 'eval_username', 'survey', 'question'])['response'].apply(lambda x: x.dropna().tolist()).reset_index()

    # Cria uma coluna para cada tipo resposta
    comments_grouped = comments_grouped.pivot_table(index=['crs_code', 'eval_username', 'survey'], columns='question', values='response', aggfunc='first').reset_index()

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
    comments_grouped['continue_doing_comments'] = comments_grouped['continue_doing_comments'].apply(tuple)
    comments_grouped['stop_doing_comments'] = comments_grouped['stop_doing_comments'].apply(tuple)
    comments_grouped['start_doing_comments'] = comments_grouped['start_doing_comments'].apply(tuple)
    
    comments_grouped['turma'] = comments_grouped['crs_code'].apply(lambda x: x.split('.')[-1]).apply(extrair_turma_e_divisao)

    return comments_grouped

def main():
    # Configurações da página
    st.title("Sistema de acompanhamento de docentes")
    st.write("Este é um sistema de acompanhamento de docentes da PGLS. Aqui você pode ver os feedbacks dos alunos sobre os professores.")
    
    # Busca os dados do banco e chama as funções responsáveis por modificar eles
    filtered_teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim, comments = fetch_data()
    responses_grouped = group_responses(filtered_teachers, responses, surveys_dim, question_dim, response_set_dim, period_dim, course_dim)
    comments_grouped = group_comments(comments, responses_grouped['schoolCourseCode'].unique())

    # Carrega os dados antigos
    old_data = pd.read_csv('src/data/surveys_old.csv')
    
    # Cria as abas para visualização dos dados
    tab_old, tab_new = st.tabs(["Feedbacks do sistema antigo", "Feedbacks do sistema novo"])
    with tab_old:
        st.subheader("Feedbacks antigos")
        st.write("Escolha os filtros para analisar os dados")
        
        # Cria uma lista de anos disponíveis para filtrar
        years_available = old_data['ano'].unique().tolist()
        years_available.sort(reverse=True)
        
        # Cria uma lista com os nomes dos professores para serem filtrados
        teachers_names = old_data['professor'].unique().tolist()
        teachers_names = [name.upper() for name in teachers_names]
        teachers_names.sort()
        
        # Cria uma lista com as turmas para serem filtradas
        turmas = old_data['turma'].unique().tolist()
        turmas.sort()
        
        # Cria os filtros
        professor = st.selectbox('Selecione o Professor', ['Todos'] + teachers_names)
        ano = st.multiselect('Selecione o ano', years_available, default=years_available)
        turma = st.selectbox('Selecione a turma', ['Todos'] + turmas)
        
        # Copia o dataframe original para filtrar
        dados_filtrados = old_data.copy()
        if professor != 'Todos':
            dados_filtrados = dados_filtrados[dados_filtrados['professor'] == professor]
        if turma != 'Todos':
            dados_filtrados = dados_filtrados[dados_filtrados['turma'] == turma]
            
        dados_filtrados = dados_filtrados[dados_filtrados['ano'].isin(ano)]
        
        # Mostra os dados filtrados
        st.write(dados_filtrados)

    with tab_new:
        # Cria uma lista de anos disponíveis para filtrar
        years_available = responses_grouped['year'].unique().tolist()
        years_available.sort(reverse=True)
        
        # Cria uma lista com os nomes dos professores para serem filtrados
        teachers_names = sorted([name.upper() for name in responses_grouped['fullName'].unique().tolist()])
        
        col1, col2 = st.columns(2)

        with col1:
            professor = st.selectbox('Selecione o Professor', ['Todos'] + teachers_names)
        
        if professor == 'Todos':
            turmas_list = responses_grouped['turma'].unique().tolist()
        else:
            turmas_list = responses_grouped[responses_grouped['fullName'] == professor]['turma'].unique().tolist()
        turmas_list.sort()
        
        with col2:
            turma = st.selectbox('Selecione a turma', ['Todos'] + turmas_list)
    
        ano = st.multiselect('Selecione o ano', years_available, default=years_available)    

        # Copia o dataframe original para filtrar
        dados_filtrados = responses_grouped.copy()
        if professor != 'Todos':
            dados_filtrados = dados_filtrados[dados_filtrados['fullName'] == professor]
            st.write("Disciplinas que esse professor ministrou:")
            st.write(dados_filtrados[['departmentName', 'courseName', 'turma']].drop_duplicates())
                        
            feedbacks = dados_filtrados.groupby(['survey', 'questionSubCategory', 'year', 'period', 'responseScale']).agg({
                'responseValue': 'mean'
            })
            
            st.write('## Avaliações')
            st.write(feedbacks)

            st.write("## Comentários")
            teachers_username = filtered_teachers[filtered_teachers['fullName'].str.upper() == professor]['coursevalUserName'].values[0]
            comments_teacher = comments_grouped[(comments_grouped['eval_username'] == teachers_username)]
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
        if turma != 'Todos' and professor == 'Todos':
            dados_filtrados = dados_filtrados[dados_filtrados['turma'] == turma]
            
            st.write("Professores que ministraram essa turma:")
            st.write(dados_filtrados[['fullName', 'courseName']].drop_duplicates())

        dados_filtrados = dados_filtrados[dados_filtrados['year'].isin(ano)]

if __name__ == "__main__":
    main()