# Sistema de acompanhamento da PGLS

**O website ainda está incompleto pois não há conexão com o banco de dados do Insper, e sim com sqlite e csv. Portanto o próximo passo é fazer essa conexão para o pleno funcionamento.**

Esse sistema foi desenvolvido durante o estágio de férias de 2025.1 no Insper. Nele é possível acompanhar os docentes e as turmas da PGLS.

Para acessar o website, basta clicar [aqui](https://www.insper-pgls.streamlit.app)

## Desenvolvimento

Esse website foi desenvolvido utilizando [python](https://www.python.org/), [pandas](https://pandas.pydata.org/docs/) e [streamlit](https://streamlit.io/).

Para continuar o desenvolvimento, clone o repositório da maneira que preferir e instale as dependências do `requirements.txt`. Depois disso crie o arquivo `.streamlit/secrets.toml`. Dentro dele coloque:

```toml
# Url do banco de dados
DATABASE_URL = ""
# API da OpenAI que faz os resumos dos comentários
OPENAI_API_KEY = ""
# Prompt para ser utilizado na geração de resumo dos comentários de um professor
TEACHER_PROMPT = "" 
# Prompt para ser utilizado na geração de resumo dos comentários de uma turma
CLASS_PROMPT = ""
```
