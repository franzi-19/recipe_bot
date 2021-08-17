import logging
from telegram.ext import CommandHandler, Updater, MessageHandler, Filters, ConversationHandler, Handler
from  chefkoch_to_markdown import markdown_gen
from dotenv import load_dotenv
import os
from os import path
import push_to_git
import tempfile
from wand.image import Image
from pathlib import Path

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

    update_repo(RECIPE_FOLDER) 
    if not _recipe_exists(RECIPE_FOLDER, filename_without_id):
        markdown = markdown_gen.get_markdown(update.message.text, recipe_id)
        with open(path_new_file,'w') as f:
            f.write(markdown)
        upload_to_git(RECIPE_FOLDER, f"added recipe {title}", path_new_file) # comment if not umpload to git
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
    max_used = max(int(found) for found in (os.path.splitext(fn)[0].split("_")[0] for fn in os.listdir(folder_path)) if found.isnumeric())
    if max_used is not None:
        return max_used+1
    else: return 0

def _recipe_exists(folder_path, filename_without_id):
    return [found for found in os.listdir(folder_path) if filename_without_id in found] != []

def update_repo(RECIPE_FOLDER):
    # TODO: Proper search for .git upwards from the recipe folder
    index = [i for i, ltr in enumerate(RECIPE_FOLDER) if ltr == '/'][-1]
    git_path = RECIPE_FOLDER[:index] + '/.git'
    push_to_git.git_pull(git_path)
    
def upload_to_git(RECIPE_FOLDER, commit_msg, *files):
    index = [i for i, ltr in enumerate(RECIPE_FOLDER) if ltr == '/'][-1]
    git_path = RECIPE_FOLDER[:index] + '/.git'
    push_to_git.git_push(git_path, commit_msg, *files)

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
        update_repo(RECIPE_FOLDER) 
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
        update_repo(RECIPE_FOLDER) 
        all_recipes = [rec for rec in os.listdir(RECIPE_FOLDER) if rec.split('_')[0].isnumeric()]
        all_recipes.sort(key=_key_for_sorting)
        for rec in all_recipes: 
            if update.message.text.lower() in rec.lower():
                found.append(rec)
        if found != []:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Not an ID, do you mean one of these recipes: {found}? Please specify an ID or type "end"')
            return CHOOSING
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='No recipe found for your input. Please specify an ID or type "end"')
            return CHOOSING

def find_line_by_predicate(f, pred, offset=0, cancel_pred=None, find_last=False):
    if str(f) == f:
        f = open(f, 'r')

    ret = None

    for line_no, line in enumerate(f):
        if line_no <= offset:
            continue
        if pred(line):
            if not find_last:
                return line_no
            else:
                ret = line_no
        if cancel_pred is not None and cancel_pred(line_no, line):
            return ret
    return ret

def ensure_line_terminations(lines):
    return [ line if line.endswith("\n") else line + "\n" for line in lines ]

def add_text_comment(chat, comment, context):
    RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")

    update_repo(RECIPE_FOLDER)
    contents = open(context.user_data['selected_recipe']).readlines()
    found_position = find_line_by_predicate(iter(contents), lambda l: 'Kommentare' in l)

    # recipe has comment section
    if found_position is not None:
        contents.insert(found_position + 1, f'* {comment}\n')
        contents = ensure_line_terminations(contents)
        with open(context.user_data['selected_recipe'],'w') as recipe_file:
            recipe_file.writelines(contents)
        context.bot.send_message(chat_id=chat, text='Successful')
        recipe_fn = os.path.splitext(os.path.basename(context.user_data['selected_recipe']))[0]
        upload_to_git(RECIPE_FOLDER, f"added comment to {recipe_fn}", context.user_data['selected_recipe']) # notify user if push or commit fails
    else:
        context.bot.send_message(chat_id=chat, text='Unable to add a comment: The recipe does not have a comment section')

    return ConversationHandler.END

def add_photo(chat, photo_sizes, caption, context):
    RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
    rid = Path(context.user_data['selected_recipe']).name.split("_")[0]

    # Find insertion point
    update_repo(RECIPE_FOLDER)
    contents = open(context.user_data['selected_recipe']).readlines()
    img_section = find_line_by_predicate(iter(contents), lambda l: l.startswith("#") and ('Bilder' in l))
    if img_section is None:
        first_section = find_line_by_predicate(iter(contents), lambda l: l.startswith("## "))
        if first_section is None:
            context.bot.send_message(chat_id=chat, text='Unable to add a photo: The recipe appears to be empty')
            return ConversationHandler.END
        # Insert new photo section if no section is found
        contents.insert(first_section, "## Bilder")
        img_section = first_section
    last_item = find_line_by_predicate(iter(contents), lambda l: l.startswith("*"), offset=img_section+1, find_last=True, cancel_pred=lambda _,l: l.startswith("#"))
    if last_item is None:
        print("Last item fallback")
        last_item = img_section
    print("Last item:", last_item)

    # Choose and download the correct file size (Closest to 800 pixels in width - this is a pretty arbitrary value)
    sz = min(photo_sizes, key=lambda sz: abs(sz.width - 800))
    if sz is None:
        context.bot.send_message(chat_id=chat, text='Unable to add a photo: No sizes available')
        return ConversationHandler.END

    # Fetch image
    img_file = tempfile.TemporaryFile()
    context.bot.get_file(sz.file_id).download(out=img_file)
    img_file.seek(0)

    # Preprocess image
    image = Image(file=img_file)
    (w,h) = image.size
    scale = 800. / w
    image.resize(int(w*scale), int(h*scale))
    image.strip()
    image = image.convert("jpg")
    image.compression_quality = 90

    # Determine filename
    recipe_img_folder = Path(RECIPE_FOLDER) / ".." / "images" / rid
    if not recipe_img_folder.exists():
        recipe_img_folder.mkdir(parents=True)

    img_id = _calculate_recipe_ID(recipe_img_folder)
    filename = str(recipe_img_folder / f"{img_id:03}.jpg")
    image.save(filename=filename)

    contents.insert(last_item+1, f"* ![{caption}](../images/{rid}/{img_id:03}.jpg)")
    contents = ensure_line_terminations(contents)
    with open(context.user_data['selected_recipe'],'w') as recipe_file:
        recipe_file.writelines(contents)

    recipe_fn = os.path.splitext(os.path.basename(context.user_data['selected_recipe']))[0]
    upload_to_git(RECIPE_FOLDER, f"added photo to {recipe_fn}", context.user_data['selected_recipe'], filename) # notify user if push or commit fails
    context.bot.send_message(chat_id=chat, text=f'Added photo')
    return ConversationHandler.END


def add_comment(update, context):
    RECIPE_FOLDER = os.getenv("RECIPE_FOLDER")
    if update.message is None:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Unable to add a comment: Got a message-less update')
        return ConversationHandler.END

    chat = update.effective_chat.id

    if (comment:=update.message.text) is not None:
        print("Adding text")
        return add_text_comment(chat, comment, context)
    elif (sizes:=update.message.photo) is not None:
        print("Adding photo")
        return add_photo(chat, sizes, update.message.caption or "Bild", context)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Unable to add a comment: Unsupported message content')
        return ConversationHandler.END

def get_chatid_set():
    chatlist = os.getenv("CHAT_IDS")
    if chatlist is not None:
        return set(int(id) for id in chatlist.split(","))

class CIDFilteredHandler(Handler):
    """
    Wrapping handler filtering by chat ids to allow us to easily create private bots.
    """
    def __init__(self, valid_cids, inner):
        self.inner = inner
        self.run_async = inner.run_async
        self.valid_cids = set(valid_cids)
    
    def check_update(self, update):
        if not update.effective_chat or (self.valid_cids is not None and update.effective_chat.id not in self.valid_cids):
            return None
        return self.inner.check_update(update)

    def handle_update(self,
                      update,
                      dispatcher,
                      check_result,
                      context= None):
        return self.inner.handle_update(update, dispatcher, check_result, context)
    
    def collect_additional_context(self,
                                   context,
                                   update,
                                   dispatcher,
                                   check_result):
        return self.inner.collect_additional_context(context, update, dispatcher, check_result)

def setup_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
    updater = Updater(token=os.getenv("BOT_TOKEN"), use_context=True)
    for upd in updater.bot.get_updates():
        print("Update on chat", upd.effective_chat.type, upd.effective_chat.id)
    dispatcher = updater.dispatcher
    
    valid_cids = get_chatid_set()

    comment_handler = ConversationHandler(
        entry_points=[CommandHandler('comment', wait_for_comment)],
        states={CHOOSING:[MessageHandler(Filters.text & (~Filters.command), choose_recipe)],
                ADDING:[MessageHandler((Filters.photo | Filters.text) & (~Filters.command), add_comment)]},
        fallbacks=[CommandHandler('help', help)])
    filtered_handler = CIDFilteredHandler(valid_cids, comment_handler)
    dispatcher.add_handler(filtered_handler)

    add_recipe_handler = MessageHandler(Filters.text & (~Filters.command), add_recipe_from_url)
    filtered_handler = CIDFilteredHandler(valid_cids, add_recipe_handler)
    dispatcher.add_handler(filtered_handler)

    # must be added last
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)
    updater.start_polling()

if __name__ == "__main__":
    load_dotenv()
    setup_bot()
