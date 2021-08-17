FROM python:3.9

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y install libmagickwand-dev
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* 

RUN mkdir -p /data/recipes
RUN mkdir -p /root/.ssh
VOLUME /data/recipes /root/.ssh
ENV RECIPE_FOLDER="/data/recipes/recipes"
COPY ./requirements.txt /opt/recipe_bot/requirements.txt
WORKDIR /opt/recipe_bot
RUN pip install -r requirements.txt
COPY . /opt/recipe_bot
CMD python recipe_bot.py
