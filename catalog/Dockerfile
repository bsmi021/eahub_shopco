FROM python:3.7.2
RUN apt-get update && apt-get -y install netcat && apt-get clean

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY config.yml ./
COPY run.sh ./
COPY catalog ./catalog/

RUN chmod +x ./run.sh

CMD ["./run.sh"]



