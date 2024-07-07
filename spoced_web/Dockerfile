from python:3

RUN mkdir /app
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD uvicorn app:app --host=0.0.0.0
