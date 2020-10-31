import logging
from telegram.ext import CommandHandler, Updater, MessageHandler, Filters, ConversationHandler
from  chefkoch_to_markdown import markdown_gen
from dotenv import load_dotenv
import os
from os import path
import push_to_git

CHOOSING, ADDING = range(2)

def add_recipe_from_url(update, context):
    if _check_if_chefkoch(update.message.text): add_chefkoch_recipe(update,context)
    else: add_unknown_recipe(update,context)
        
#TODO
def add_unknown_recipe(update, context):
    # markdown = markdown_gen.get_markdown(update.message.text, recipe_id)
    context.bot.send_message(chat_id=update.effective_chat.id, text='Not a chefkoch recipe')

def add_chefkoch_recipe(update, context):
    RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
    recipe_id = _calculate_recipe_ID(RECIPE_FOLDER)
    title = markdown_gen.get_title(update.message.text)
    filename_without_id = _new_filename_from_title(title)
    path_new_file = RECIPE_FOLDER + f'/{recipe_id}_{filename_without_id}.md'

    if not _recipe_exists(RECIPE_FOLDER, filename_without_id):
        markdown = markdown_gen.get_markdown(update.message.text, recipe_id)
        with open(path_new_file,'w') as f:
            f.write(markdown)
        upload_to_git(RECIPE_FOLDER, title, path_new_file) # comment if not umpload to git
        context.bot.send_message(chat_id=update.effective_chat.id, text='Successful')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Recipe "{title}" already exists')

def _new_filename_from_title(title):
    chars = {'ö':'oe', 'ä':'ae', 'ü':'ue', 'ß':'ss', '-':'_', ' ':'_', '__':'_'} 
    title = title.lower()
    for i in chars:
        title = title.replace(i,chars[i])

    return title

def _check_if_chefkoch(url):
    return 'chefkoch' in url


def _calculate_recipe_ID(folder_path):
    files = os.listdir(folder_path)
    files = [found for found in os.listdir(folder_path) if found.split('_')[0].isnumeric()]
    files.sort(reverse=True, key=_key_for_sorting)
    if files != None and files != []:
        return int(files[0].split('_')[0])+1
    else: return 0

def _key_for_sorting(elem):
    return int(elem.split('_')[0])

def _recipe_exists(folder_path, filename_without_id):
    return [found for found in os.listdir(folder_path) if filename_without_id in found] != []
    

# TODO: create gitpath better, maybe also in .env
def upload_to_git(RECIPE_FOLDER, title, path_new_file):
    index = [i for i, ltr in enumerate(RECIPE_FOLDER) if ltr == '/'][-1]
    git_path = RECIPE_FOLDER[:index] + '/.git'
    push_to_git.git_push(git_path, f'added recipe {title}', path_new_file)

def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot to manage recipes. Just send me urls to recipes (presumably to chefkoch.de)")

def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

def wait_for_comment(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Great, for which recipe do you want to write a comment? State the ID")
    return CHOOSING


def choose_recipe(update, context):
    # leave conversation
    if update.message.text == 'end':
        context.bot.send_message(chat_id=update.effective_chat.id, text='Abort')
        return ConversationHandler.END
    # maybe an ID
    elif update.message.text.isnumeric():
        found = ''
        RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
        all_recipes = [rec for rec in os.listdir(RECIPE_FOLDER) if rec.split('_')[0].isnumeric()]
        for rec in all_recipes: 
            if int(rec.split('_')[0]) == int(update.message.text):
                context.user_data['selected_recipe'] = f'{RECIPE_FOLDER}/{rec}'
                found = rec
        # recipe with that ID exists
        if found != '':
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"You've selected '{found}'. What is your comment?")
            return ADDING
        # not an valid ID
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='No recipe found under this ID. Please specify an existing ID or type "end"')
            return CHOOSING
    # not an valid ID but maybe part of a title
    else:
        found = []
        RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
        all_recipes = [rec for rec in os.listdir(RECIPE_FOLDER) if rec.split('_')[0].isnumeric()]
        all_recipes.sort(key=_key_for_sorting)
        for rec in all_recipes: 
            if update.message.text in rec:
                found.append(rec)
        if found != []:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Not an ID, do you mean one of these recipes: {found}? Please specify an ID or type "end"')
            return CHOOSING
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='No recipe found for your input. Please specify an ID or type "end"')
            return CHOOSING

def add_comment(update, context):
    comment = update.message.text
    found_position = 0
    contents = []

    with open(context.user_data['selected_recipe'], 'r') as recipe_file:
        contents = recipe_file.readlines()
        for index, line in enumerate(contents):
            if 'Kommentare' in line:
                found_position = index

    # recipe has comment section
    if found_position != 0:
        contents.insert(found_position +1, f'* {comment}\n')
        with open(context.user_data['selected_recipe'],'w') as recipe_file:
            recipe_file.writelines(contents)
        context.bot.send_message(chat_id=update.effective_chat.id, text='Successful')
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Unable to add a comment: The recipe does not have a comment section')

    return ConversationHandler.END

def setup_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
    updater = Updater(token=os.getenv("BOT_TOKEN"), use_context=True)
    dispatcher = updater.dispatcher

    comment_handler = ConversationHandler(
        entry_points=[CommandHandler('comment', wait_for_comment)],
        states={CHOOSING:[MessageHandler(Filters.text & (~Filters.command), choose_recipe)],
                ADDING:[MessageHandler(Filters.text & (~Filters.command), add_comment)]},
        fallbacks=[CommandHandler('help', help)])
    dispatcher.add_handler(comment_handler)

    add_recipe_handler = MessageHandler(Filters.text & (~Filters.command), add_recipe_from_url)
    dispatcher.add_handler(add_recipe_handler)

    # must be added last
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)
    updater.start_polling()

if __name__ == "__main__":
    load_dotenv()
    setup_bot()
