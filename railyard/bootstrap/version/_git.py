import sys
import subprocess

from railyard.bootstrap.version import VersionParser

try:
    import git
except ImportError:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "GitPython"]
    )
    import git

    del sys.modules["git"]
    subprocess.check_call(
        [sys.executable, "-m", "pip", "uninstall", "GitPython"]
    )


@VersionParser.plugin("git")
def _() -> str:
    repo = git.Repo()
    if repo.bare:
        raise RuntimeError(
            f"The repo at '{repo.working_dir}' cannot be empty!"
        )
    head_commit = repo.head.commit
    try:
        tag = repo.tags[-1]
    except IndexError:
        tag_name = "0"
        tag_commit = None
    else:
        tag_name = tag.name
        tag_commit = tag.commit
    public, *local = tag_name.split("+")
    if head_commit != tag_commit:
        commit_label = head_commit.hexsha
        local.append(commit_label)
    dirty = repo.index.diff(None) or repo.untracked_files
    if dirty:
        local.append("dirty")
    return f"{public}+{'.'.join(local)}" if local else public
