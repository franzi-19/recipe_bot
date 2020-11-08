FROM python:3.9
COPY . /opt/recipe_bot
WORKDIR /opt/recipe_bot
RUN pip install -r requirements.txt
CMD python recipe_bot.py