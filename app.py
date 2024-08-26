from langchain_openai import ChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.chains.graph_qa.cypher_utils import CypherQueryCorrector, Schema
from langchain_community.graphs import Neo4jGraph
import streamlit as st

### Инициализируем граф
graph = Neo4jGraph(url="bolt://neo4j_graph:7687", username='neo4j', password='12345678')

### Инициализируем llm
llm = ChatOpenAI(openai_api_base=<CURL>,
                model_name="Qwen/Qwen2-7B-Instruct",
                openai_api_key='Not needed for local server',
                temperature=0,
                max_tokens=2000)

### Entity extraction
examples = [
    {
        "query": '''Используйте указанный формат для извлечения информации из следующих входных данных. Перечислите через запятую названия всех сущностей в следующем тексте, используя все варианты перестановки слов и регистра первой буквы каждого слова: Что включено в программу детская санаторно-курортная?''',
        "answer": '''"детская санаторно-курортная", "санаторно-курортная детская", "Детская санаторно-курортная", "Санаторно-курортная детская", "Санаторно-курортная Детская", "Детская Санаторно-курортная", "Детская", "детская", "Санаторно-курортная", "санаторно-курортная"'''
    },
    {
        "query": '''Используйте указанный формат для извлечения информации из следующих входных данных. Перечислите через запятую названия всех сущностей в следующем тексте, используя все варианты перестановки слов и регистра первой буквы каждого слова: Где располагается санаторий «aiso Плаза»?''',
        "answer": '''"«aiso Плаза", "«Плаза aiso", "«Aiso Плаза", "«aiso плаза", "«Aiso плаза", "плаза Aiso", "Плаза Aiso", "aiso", "Aiso", "Плаза", "плаза"'''
    },
    {
        "query": '''Используйте указанный формат для извлечения информации из следующих входных данных. Перечислите через запятую названия всех сущностей в следующем тексте, используя все варианты перестановки слов и регистра первой буквы каждого слова: Какая цена стандартного номера?''',
        "answer": '''"«стандартный номер", "«номер стандартный", "«Стандартный номер", "«стандартный Номер", "«Стандартный Номер", "номер Стандартный ", "Номер стандартный", "Номер Стандартный", "номер", "Номер", "стандартный", "Стандартный"'''
    },
]

# создаём template для примеров
example_template = """User: {query}
AI: {answer}
"""

# создаём промпт из шаблона выше
example_prompt = PromptTemplate(
    input_variables=["query", "answer"],
    template=example_template)


# теперь разбиваем наш предыдущий промпт на prefix и suffix
# где - prefix это наша инструкция для модели
prefix = """# Инструкции по извлечению сущностей для QWEN
## 1. Обзор
Вы - алгоритм высшего уровня, предназначенный для извлечения информации в структурированных форматах.
- ** Узлы ** представляют сущности и концепции. Они похожи на узлы Википедии.
## 2. Маркировка узлов
- ** Согласованность **: Убедитесь, что вы используете базовые или элементарные типы для маркировки узлов.
- ** Идентификаторы узлов **: Никогда не используйте целые числа в качестве идентификаторов узлов. Идентификаторы узлов должны быть именами или удобочитаемыми идентификаторами, найденными в тексте.
## 3. Ответ
Ответ должен содержать:
1) Все сущности в тексте;
2) Различные варианты перестановок слов внутри каждой сущности;
3) Различные варианты регистров первых букв первого слова;
4) Каждое слово сущности в именительном падеже, например: вешалка, утюг, петарда.
## 4. Строгое соблюдение
Строго соблюдайте правила. Несоблюдение приведет к увольнению.
Вот пример:"""

suffix = '''
User: Используйте указанный формат для извлечения информации из следующих входных данных. Перечислите через запятую названия всех сущностей в следующем тексте, используя все варианты перестановки слов и регистра первой буквы каждого слова: {input}
Совет: Убедитесь, что ответ дан в правильном формате.
AI:
'''

# создаём сам few shot prompt template
few_shot_prompt_template = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix=prefix,
    suffix=suffix,
    input_variables=["input"],
    example_separator="\n\n"
)

# Цепочка для извлечения сущностей из вопроса
entity_chain = few_shot_prompt_template | llm | StrOutputParser()

### Mapping
def map_to_database(values):
    try:
        values = eval(values)
    except:
        values = eval(values[:values.rfind('"')])

    result = ""
    for entity in values:
        response = graph.query(match_query, {"value": entity})
        try:
            result += f"{entity} сопоставляется с {response[0]['id']} {response[0]['type']} из базы данных\n"
        except IndexError:
            pass
    return result
    
match_query = """MATCH (n)
WHERE n.id CONTAINS $value
RETURN n.id AS id, labels(n)[0] AS type
LIMIT 1
"""

### Генерация cypher запроса
examples = [
    {
        "question": "Что включает в себя Программа «Санаторно курортное лечение»?",
        "query": '''MATCH (p:Программа {{id: "Программа «Санаторно курортное лечение»"}})-[:ВКЛЮЧАЕТ]->(u) RETURN u'''
    },
]

example_prompt = PromptTemplate.from_template(
    '''User: {question}
Cypher query: {query}'''
)

prefix = '''Вы эксперт по Neo4j. Получив входной вопрос, создайте синтаксически корректный cypher запрос для выполнения.
Вот информация о схеме
{schema}.

Сущности в вопросе сопоставляются со следующими значениями базы данных:
{entities_list}

Ниже приведен ряд примеров вопросов и соответствующих им cypher запросов.'''

suffix = '''User: {input}
Указание: Ваш ответ не должен содержать ничего кроме cypher запроса.
Cypher query: '''

cypher_prompt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix=prefix,
    suffix=suffix,
    input_variables=["input", "schema", "entities_list"],
)

# Цепочка генерации cypher запроса
cypher_response = (
    RunnablePassthrough.assign(names=entity_chain)
    | RunnablePassthrough.assign(
        entities_list=lambda x: map_to_database(x["names"]),
        schema=lambda _: graph.get_schema,
    )
    | cypher_prompt
    | llm.bind(stop=["\nCypherResult:"])
    | StrOutputParser()
)

### Генерация финального ответа
corrector_schema = [
    Schema(el["start"], el["type"], el["end"])
    for el in graph.structured_schema.get("relationships")
]
cypher_validation = CypherQueryCorrector(corrector_schema)

response_template = """Основываясь на вопросе, Cypher query и Cypher Response, напишите ответ на естественном языке:
Question: {input}
Cypher query: {query}
Cypher Response: {response}"""

response_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Получив входной вопрос и Cypher response, преобразуйте его в ответ на естественном языке"
        ),
        ("human", response_template),
    ]
)

# Цепочка генерации финального ответа
chain = (
    RunnablePassthrough.assign(query=cypher_response)
    | RunnablePassthrough.assign(
        response=lambda x: graph.query(cypher_validation(x["query"])),
    )
    | response_prompt
    | llm
    | StrOutputParser()
)

### ИНТЕРФЕЙС
def question_answering(qa_chain, question):
    try:
        answer = qa_chain.invoke({"input": question})
    except:
        answer = "Что-то пошло не так...\nПопробуйте перефразировать вопрос и попробовать ещё раз."
    st.info(answer)

st.title("Вопрос-ответ")

with st.form("my_form"):
    text = st.text_area("Введите вопрос:", "Какие есть программы?")
    submitted = st.form_submit_button("Отправить")
    if submitted:
        question_answering(chain, text)