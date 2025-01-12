import streamlit as st
from tools import fetch_data_as_json
import openai
from dotenv import load_dotenv
import os

"""
This script creates a Streamlit app that allows users to interact with a PostgreSQL database using natural language queries. 
It uses OpenAI's API to generate SQL queries based on user input and fetches data from the database. 
The results are then displayed in the app, along with the generated SQL query.

Key components:
- Load environment variables for API keys and endpoints.
- Define a function `chat_with_postgresql` to generate SQL queries and fetch data.
- Use Streamlit to create a user interface for input and display results.
"""

load_dotenv()

BASE_URL = os.getenv('LITELLM_HOST')
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME')
LITE_LLM_KEY = os.getenv('LITE_LLM_KEY')

client = openai.OpenAI(
    api_key=LITE_LLM_KEY,
    base_url=BASE_URL
)

def chat_with_postgresql(user_prompt: str):
    get_schema_query = """
    SELECT 
        table_schema,
        table_name,
        STRING_AGG(column_name || ' (' || data_type || ')', ', ') AS columns
    FROM 
        information_schema.columns
    WHERE 
        table_schema NOT IN ('information_schema', 'pg_catalog')
    GROUP BY 
        table_schema, table_name
    ORDER BY 
        table_schema, table_name;
    """
    schema = fetch_data_as_json(get_schema_query)


    system_prompt_query = f"""
        You are an AI assistant that creates t-sql query based on postgresql database. 
        You will be given table schema, and the user query. You will response with the t-sql query to fetch the data based on the user query.
        Only respond with the sql query, do not include explanation.
        table schema: {schema}
    """

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt_query,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
    )

    print(response.choices[0].message.content)

    sql_query = response.choices[0].message.content
    sql_query = sql_query.replace("```sql", "").replace("```", "")

    data = fetch_data_as_json(sql_query)

    generate_response_prompt = f"""
        You are an AI assistant that generate user response based on the data fetched from postgresql database.
        You will be given the data fetched from the database. You will response with the user response.
        You only answer based on data, and says 'I don't have access to the data' if the data is empty.
        data: {data}
    """

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": generate_response_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
    )

    answer = response.choices[0].message.content

    return answer, sql_query

st.title('👨‍💻 Chat with PostgreSQL')

input_text = st.text_area('User Query', value='')

if st.button('Execute'):
    response, sql_query = chat_with_postgresql(input_text)
    st.markdown(response)

    with st.expander('Show SQL Query'):
        st.code(sql_query)



