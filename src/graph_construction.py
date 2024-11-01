import streamlit as st
from stqdm import stqdm
from langchain import FewShotPromptTemplate, PromptTemplate
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.graphs.graph_document import (
    Node as BaseNode,
    Relationship as BaseRelationship,
    GraphDocument,
)

def load_raw_text(path_to_file: str) -> str:
    '''
    Загружает сырой текст.

    Args:
        path_to_file (str): Путь до файла.
    Returns:
        result (str): Текст из исходного файла.
    '''
    result = ""
    with open(path_to_file, "r", encoding="utf-8") as fl:
        for line in fl:
            result += line
    return result

def graph_construction(split_documents: list[Document], splitter_for_gpt: RecursiveCharacterTextSplitter):
    '''
    Основная функция для извлечения сущностей и связей из текста, и добавления их в граф.
    
    Args:
        split_documents (list[Document]): Список чанков из исходного документа. 
        splitter_for_gpt (RecursiveCharacterTextSplitter): Сплиттер, чтобы разбить "ошибочный" чанк для контекстного окна gpt.
    '''
    for document in stqdm(split_documents):
        ans = llm_qwen.invoke(few_shot_prompt_template_qwen.format(input=document), max_tokens=5000).content
        try:
            ans = eval(ans[:ans.rfind("}")+1])
            graph_document = GraphDocument(
                                    nodes = ans.get('nodes'),
                                    relationships = ans.get('relationships'),
                                    source = document
            )
            graph.add_graph_documents([graph_document])
        except:
            gpt_helper(document, splitter_for_gpt)

def gpt_helper(document: Document, splitter: RecursiveCharacterTextSplitter):
    '''
    Дополнительная функция для извлечения сущностей и связей из текста, и добавления их в граф.
    Используется в случаях, когда ответ основной модели вызывает ошибку.
    
    Args:
        document (Document): Чанк, на котором ошиблась основная модель.
        splitter (RecursiveCharacterTextSplitter): Рекурсивный сплиттер.
    '''
    new_documents = splitter.create_documents([str(document)])
    for doc in new_documents:
        ans = llm_gpt.invoke(few_shot_prompt_template_gpt.format(input=document)).content
        try:
            ans = eval(ans[:ans.rfind("}")+1])
            graph_document = GraphDocument(
                                    nodes = ans.get('nodes'),
                                    relationships = ans.get('relationships'),
                                    source = document
            )
            graph.add_graph_documents([graph_document])
        except:
            continue

### Инициализируем граф
graph = Neo4jGraph(url="bolt://neo4j_graph:7687", username='neo4j', password='12345678')

### Инициализируем llm модели
llm_qwen = ChatOpenAI(openai_api_base=<CURL>,
                model_name="Qwen/Qwen2-7B-Instruct",
                openai_api_key='Not needed for local server',
                temperature=0)

llm_gpt = ChatOpenAI(openai_api_key=<API_KEY>,
                 model="gpt-3.5-turbo", temperature=0)

### Строим промпт для извлечения сущностей и связей из сырого текста
examples = [
    {
        "query": '''Используйте указанный формат для извлечения информации из следующих входных данных: Мария Кюри, родилась в 1867 году. Ее муж, Пьер Кюри, был одним из лауреатов ее первой Нобелевской премии.
        В 1906 году она стала первой женщиной, ставшей профессором Парижского университета.''',
        "answer": '''{{"nodes": [BaseNode(id='Мария Кюри', type='Человек', properties={{'год_рождения': '1867'}}), BaseNode(id='Пьер Кюри', type='Человек'), BaseNode(id='Парижский Университет', type='Организация')], "relationships": [BaseRelationship(source=BaseNode(id='Мария Кюри', type='Человек'), target=BaseNode(id='Пьер Кюри', type='Человек'), type='Супруг'), BaseRelationship(source=BaseNode(id='Мария Кюри', type='Человек'), target=BaseNode(id='Парижский Университет', type='Организация'), type='Работала')]}}'''
    }
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
prefix_qwen = """# Инструкции по построению графа знаний для QWEN
## 1. Обзор
Вы - алгоритм высшего уровня, предназначенный для извлечения информации в структурированных форматах для построения графа знаний.
- ** Узлы ** представляют сущности и концепции. Они похожи на узлы Википедии.
- Цель состоит в том, чтобы добиться простоты и ясности в графе знаний, сделав его доступным для широкой аудитории.
## 2. Маркировка узлов
- ** Согласованность **: Убедитесь, что вы используете базовые или элементарные типы для маркировки узлов.
  - Например, когда вы идентифицируете объект, представляющий человека, всегда помечайте его как "человек". Избегайте использования более специфичных терминов, таких как "математик" или "ученый".
- ** Идентификаторы узлов **: Никогда не используйте целые числа в качестве идентификаторов узлов. Идентификаторы узлов должны быть именами или удобочитаемыми идентификаторами, найденными в тексте.
## 3. Идентификация и обработка таблиц
- **Обнаружение таблиц**: Идентификация таблиц по ключевому слову "Таблица" в текстовом документе.
- **Извлечение сущностей и связей**: Извлекайте сущности и их связи из таблиц. Рассмотрите строки, столбцы и заголовки для понимания контекста.
## 4. Обработка числовых данных и дат
- Числовые данные, такие как возраст или другая связанная с ними информация, должны быть включены в качестве атрибутов или свойств соответствующих узлов.
- ** Никаких отдельных узлов для дат/чисел**: Не создавайте отдельные узлы для дат или числовых значений. Всегда добавляйте их в качестве атрибутов или свойств узлов.
- **Формат свойств**: Свойства должны быть в формате ключ-значение.
- **Кавычки**: Никогда не используйте экранированные одинарные или двойные кавычки в значениях свойств.
## 5. Разрешение кореференции
- ** Поддерживать согласованность сущностей **: При извлечении сущностей очень важно обеспечить согласованность.
Если объект, такой как "Джон Доу", упоминается в тексте несколько раз, но его называют разными именами или местоимениями (например, "Джо", "он"),
всегда используйте наиболее полный идентификатор этого объекта в графе знаний. В этом примере используйте "Джон Доу" в качестве идентификатора объекта.  
Помните, что граф знаний должен быть последовательным и легко понятным, поэтому крайне важно поддерживать согласованность в ссылках на объекты. 
## 6. Результат
Представьте результат так, чтобы его можно было отправить в neo4j graph. Выдача примеров за ответ будет караться штрафом!
## 7. Повторы
Избегайте повторов BaseNode и BaseRelationship!
## 8. Строгое соблюдение
Строго соблюдайте правила. Несоблюдение приведет к увольнению.
Вот пример:"""

prefix_gpt = '''
Инструкции по построению графа знаний для GPT
1. Обзор
Вы - алгоритм высшего уровня, предназначенный для извлечения информации в структурированных форматах для построения графа знаний.
- ** Узлы ** представляют сущности и концепции. Они похожи на узлы Википедии.
- Цель состоит в том, чтобы добиться простоты и ясности в графе знаний, сделав его доступным для широкой аудитории.
2. Маркировка узлов
- ** Согласованность **: Убедитесь, что вы используете базовые или элементарные типы для маркировки узлов.
  - Например, когда вы идентифицируете объект, представляющий человека, всегда помечайте его как **"персона"**. Избегайте использования более специфичных терминов, таких как "математик" или "ученый".
- ** Идентификаторы узлов **: Никогда не используйте целые числа в качестве идентификаторов узлов. Идентификаторами узлов должны быть имена или понятные пользователю идентификаторы, которые можно найти в тексте.
- помните, что свойства - это набор строк.
3. Идентификация и обработка таблиц
- ** Обнаружение таблиц**: Идентификация таблиц по ключевому слову "Таблица" в текстовом документе.
- **Извлечение сущностей и связей**: Извлекайте сущности и их связи из таблиц. Рассмотрите строки, столбцы и заголовки для понимания контекста.
4. Обработка числовых данных и дат.
- Числовые данные, такие как возраст или другая связанная с ними информация, должны быть включены в качестве атрибутов или свойств соответствующих узлов.
- ** Никаких отдельных узлов для дат/чисел**: Не создавайте отдельные узлы для дат или числовых значений. Всегда добавляйте их в качестве атрибутов или свойств узлов.
- **Кавычки**: Никогда не используйте экранированные одинарные или двойные кавычки в значениях свойств.
5. Разрешение параллелизма
- **Поддержание согласованности сущностей**: При извлечении сущностей важно обеспечить согласованность.
Если объект, такой как "Джон Доу", упоминается в тексте несколько раз, но его называют разными именами или местоимениями (например, "Джо", "он"),
всегда используйте наиболее полный идентификатор этого объекта в графе знаний. В этом примере используйте "Джон Доу" в качестве идентификатора объекта.  
Помните, что граф знаний должен быть последовательным и легко понятным, поэтому крайне важно поддерживать согласованность в ссылках на сущности. 
## 6. Важно
Не дублируйте ответ.
Не забудьте закрыть скобки!
Не забывайте строить новые nodes и relationships!
7. Скобки
Закрывайте открытые скобки! Например, в BaseNode(), properties={{}}!
8. Строгое соблюдение
Строго придерживайтесь правил. Несоблюдение приведет к увольнению.
Вот несколько примеров:"""
'''

# а suffix - это вопрос пользователя и поле для ответа
suffix = '''
User: Используйте указанный формат для извлечения информации из следующих входных данных: {input}
Совет: Избегай повторов! Убедитесь, что ответ дан в правильном формате, обратите внимание на формат узлов, свойств и связей: 3 параметра должны быть внутри BaseRelationship!
AI:
'''

# создаём сам few shot prompt template
few_shot_prompt_template_gpt = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix=prefix_gpt,
    suffix=suffix,
    input_variables=["input"],
    example_separator="\n\n"
)

few_shot_prompt_template_qwen = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix=prefix_qwen,
    suffix=suffix,
    input_variables=["input"],
    example_separator="\n\n"
)

### Загружаем данные
doc_train = load_raw_text("../data/data.txt")
doc_eval = load_raw_text("../data/eval_data.txt")
docs = [doc_train, doc_eval]

### Для чанкинга будем использовать рекурсивный текст сплиттер
splitter_for_qwen = RecursiveCharacterTextSplitter(
    chunk_size=1888,  
    chunk_overlap=20,  
    length_function=len,  
)

splitter_for_gpt = RecursiveCharacterTextSplitter(
    chunk_size=1700, 
    chunk_overlap=20,  
    length_function=len, 
)

### ИНТЕРФЕЙС
st.title("Построить граф онлайн без смс регистраций (~25 минут)")

if st.button("Построить граф"):
    graph.query("MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r")
    for doc in stqdm(docs):
        split_documents = splitter_for_qwen.create_documents([doc])
        graph_construction(split_documents, splitter_for_gpt)
