FROM python:3.13
RUN mkdir /app
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- --default-toolchain 1.87 --profile minimal -y
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD uvicorn app:app --host=0.0.0.0
