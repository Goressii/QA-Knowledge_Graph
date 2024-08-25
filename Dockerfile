# FROM python:3.9
# COPY . /app
# WORKDIR /app
# RUN pip install -r requirements.txt
# EXPOSE 8501
# #ENTRYPOINT ["streamlit","run"]
# ENV VIRTUAL_ENV=/app/.venv
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"
# CMD ["streamlit", "run", "main.py"]
# #CMD ["app.py"]

# FROM python:3.9
# WORKDIR /app
# COPY requirements.txt ./requirements.txt
# RUN pip3 install -r requirements.txt
# EXPOSE 8501
# COPY . /app
# #ENTRYPOINT ["streamlit","run"]
# #CMD ["main.py"]
# ENTRYPOINT [".venv/bin/python", "-m", "streamlit", "run", "main.py"]

# FROM python:3.9

# EXPOSE 8501

# RUN apt-get update && apt-get install -y \
#     build-essential \
#     software-properties-common \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# COPY . /app

# RUN pip3 install -r requirements.txt

# ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]


# FROM python:3.9 as py-build

# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     software-properties-common \
#     && rm -rf /var/lib/apt/lists/*


# RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -

# COPY . /app
# WORKDIR /app
# ENV PATH=/opt/poetry/bin:$PATH
# RUN poetry config virtualenvs.in-project true && poetry install

# FROM python:3.9

# EXPOSE 8501
# HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
# COPY --from=py-build /app /app
# WORKDIR /app
# ENTRYPOINT [".venv/bin/python", "-m", "streamlit", "run", "mtcc/app.py", "--server.port=8501", "--server.address=0.0.0.0"]


FROM python

WORKDIR /app

# dont write pyc files
# dont buffer to stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /app/requirements.txt

# dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && rm -rf /root/.cache/pip

COPY ./ /app