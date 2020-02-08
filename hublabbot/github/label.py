"""Module for labels setup in GitHub repo."""
import github  # type: ignore
import github.Repository as ghr  # type: ignore
from github import Github

from hublabbot.settings import RepoOptions


def _has_in_labels(repo: ghr.Repository, lname: str) -> bool:
	try:
		repo.get_label(lname)
		return True
	except github.UnknownObjectException:
		return False


def _create(repo: ghr.Repository, lname: str, lcolor: str, ldescription: str) -> None:
	repo.create_label(lname, lcolor.lstrip('#'), ldescription)
	print(f'GH:{repo.full_name}: Label "{lname}" created.')


def configure(token: str, repo_options: RepoOptions) -> None:
	"""Configure labels in GitHub repo."""
	if repo_options.gh_auto_merge_pr is None:
		return
	github = Github(token)
	repo = github.get_repo(repo_options.gh_repo_path, lazy=True)
	if not _has_in_labels(repo, repo_options.gh_auto_merge_pr.required_label_name):
		_create(repo, repo_options.gh_auto_merge_pr.required_label_name,
		        repo_options.gh_auto_merge_pr.required_label_color,
		        repo_options.gh_auto_merge_pr.required_label_description)
