import logging
from telegram.ext import CommandHandler, Updater, MessageHandler, Filters
from  chefkoch_to_markdown import markdown_gen
from dotenv import load_dotenv
import os
import push_to_git

def add_recipe_from_url(update, context):
    markdown, title = markdown_gen.get_markdown(update.message.text)
    filename = title.replace(" ", "_").lower()
    RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
    path_new_file = RECIPE_FOLDER + f'/{filename}.md'

    with open(path_new_file,'w') as f:
        f.write(markdown)
    upload_to_git(RECIPE_FOLDER, title, path_new_file)

    context.bot.send_message(chat_id=update.effective_chat.id, text='successful')

# TODO: create gitpath better, maybe also in .env
def upload_to_git(RECIPE_FOLDER, title, path_new_file):
    index = [i for i, ltr in enumerate(RECIPE_FOLDER) if ltr == '/'][-1]
    git_path = RECIPE_FOLDER[:index] + '/.git'
    push_to_git.git_push(git_path, f'added recipe {title}', path_new_file)

def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot to manage recipes. Just send me url to recipes (presumably to chefkoch.de)")

def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

def setup_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
    updater = Updater(token=os.getenv("BOT_TOKEN"), use_context=True)
    dispatcher = updater.dispatcher

    add_recipe_handler = MessageHandler(Filters.text & (~Filters.command), add_recipe_from_url)
    dispatcher.add_handler(add_recipe_handler)

    # must be added last
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)
    updater.start_polling()

if __name__ == "__main__":
    load_dotenv()
    setup_bot()
