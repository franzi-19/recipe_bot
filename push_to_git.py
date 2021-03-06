from git import Repo
import sys

# TODO how to specify the branch
def git_push(path_to_repo, commit_message, path_new_file):
    try:
        repo = Repo(path_to_repo)
        repo.git.add(path_new_file)
        repo.index.commit(commit_message)
        origin = repo.remote(name='origin')
        origin.push()

    except Exception as error:
        print('Some error occured while pushing the code', error, file=sys.stderr)    

def git_pull(path_to_repo):
    try:
        repo = Repo(path_to_repo)
        repo.git.fetch()
        repo.git.merge('-X', 'theirs', '-m', 'BOT: Merge changes into local branch', '--log', 'origin/master')
    
    except Exception as error:
        print('Some error occured while pulling updates', error, file=sys.stderr)    

