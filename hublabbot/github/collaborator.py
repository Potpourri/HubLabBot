"""Module for collaborators setup in GitHub repo."""
import github.Repository as ghr  # type: ignore
import github.AuthenticatedUser as gha  # type: ignore
from github import Github

from hublabbot.settings import RepoOptions


def _add(repo: ghr.Repository, bot: gha.AuthenticatedUser) -> None:
	repo.add_to_collaborators(bot.login)
	invitation = repo.get_pending_invitations()[0]
	bot.accept_invitation(invitation)
	print(f'GH:{repo.full_name}: "{bot.login}" added to collaborators.')


def _remove(repo: ghr.Repository, bot: gha.AuthenticatedUser) -> None:
	repo.remove_from_collaborators(bot.login)
	print(f'GH:{repo.full_name}: "{bot.login}" removed from collaborators.')


def configure(token: str, bot_token: str, repo_options: RepoOptions) -> None:
	"""Configure collaborators in GitHub repo."""
	github = Github(token)
	repo = github.get_repo(repo_options.gh_repo_path, lazy=True)
	github_bot = Github(bot_token)
	bot = github_bot.get_user()
	if repo_options.gh_auto_merge_pr is not None:
		if not repo.has_in_collaborators(bot.login):
			_add(repo, bot)
	else:
		if repo.has_in_collaborators(bot.login):
			_remove(repo, bot)
