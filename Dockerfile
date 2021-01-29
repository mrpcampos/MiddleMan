FROM python:3.7.3

WORKDIR /MiddleMan

COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

COPY src/ .
COPY client-schema.json .
COPY offers-schema.json .
COPY proposal-schema.json .

RUN python manage.py db init
RUN python manage.py db migrate
RUN python manage.py db upgrade

CMD [ "flask", "run" ]
