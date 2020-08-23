import logging
from telegram.ext import CommandHandler, Updater, MessageHandler, Filters
from  chefkoch_to_markdown import markdown_gen
from dotenv import load_dotenv
import os
from os import path
import push_to_git


def add_recipe_from_url(update, context):
    if _check_if_chefkoch(update.message.text): add_chefkoch_recipe(update,context)
    else: add_unknown_recipe(update,context)
        
#TODO
def add_unknown_recipe(update, context):
    markdown = markdown_gen.get_markdown(update.message.text, recipe_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text='not a chefkoch recipe')

def add_chefkoch_recipe(update, context):
    RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
    recipe_id = _calculate_recipe_ID(RECIPE_FOLDER)
    title = markdown_gen.get_title(update.message.text)
    filename_without_id = title.replace(" ", "_").lower()
    path_new_file = RECIPE_FOLDER + f'/{recipe_id}_{filename_without_id}.md'

    if not _recipe_exists(RECIPE_FOLDER, filename_without_id):
        markdown = markdown_gen.get_markdown(update.message.text, recipe_id)
        with open(path_new_file,'w') as f:
            f.write(markdown)
        upload_to_git(RECIPE_FOLDER, title, path_new_file)
        context.bot.send_message(chat_id=update.effective_chat.id, text='successful')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'recipe "{title}" already exists')

def _check_if_chefkoch(url):
    return 'chefkoch' in url


def _calculate_recipe_ID(folder_path):
    files = os.listdir(folder_path)
    files = [found for found in os.listdir(folder_path) if found.split('_')[0].isnumeric()]
    files.sort(reverse=True)
    if files != None and files != []: return int(files[0].split('_')[0])+1
    else: return 0

def _recipe_exists(folder_path, filename_without_id):
    return [found for found in os.listdir(folder_path) if filename_without_id in found] != []
    

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
