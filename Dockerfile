FROM python:3.9
RUN mkdir -p /data/recipes
RUN mkdir -p /root/.ssh
VOLUME /data/recipes /root/.ssh
ENV RECIPE_FOLDER="/data/recipes/recipes"
COPY ./requirements.txt /opt/recipe_bot/requirements.txt
WORKDIR /opt/recipe_bot
RUN pip install -r requirements.txt
COPY . /opt/recipe_bot
CMD python recipe_bot.py