"""Warn when the running gateway's code is a git work tree someone can rebase.

A gateway launched straight from a checkout imports its code from that
checkout's files. Pooled MCP backends it spawns later import the same files
again, so a ``git rebase`` / ``checkout`` / ``pull`` in that directory while the
gateway is up hands them a mix of old and new modules. The failure is far from
its cause -- in one outage every tool-policy read failed for hours -- so the boot
log names the risk up front, where an operator reading it will look first.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def git_work_tree_root(path: Path) -> Path | None:
    """The nearest directory at or above ``path`` that holds a ``.git`` entry.

    ``.git`` is a directory in a main clone and a file in a linked worktree; both
    count. Only ``stat`` calls, no ``git`` subprocess, so boot pays no spawn.
    A copy installed under ``site-packages`` is not the checkout's files even
    when its venv lives inside one, so the walk stops there.
    """
    for candidate in (path, *path.parents):
        if candidate.name == "site-packages":
            return None
        try:
            if (candidate / ".git").exists():
                return candidate
        except OSError:
            return None
    return None


def warn_if_running_from_git_checkout(package_dir: Path | None = None) -> Path | None:
    """Log one WARNING when ``package_dir`` sits inside a git work tree.

    Returns the work tree's root (or ``None``) so the caller and tests can see
    what was found. Never raises: a boot step that only warns must not stop boot.
    """
    try:
        if package_dir is None:
            package_dir = Path(__file__).resolve().parent
        root = git_work_tree_root(package_dir)
    except Exception:
        logger.debug("live-checkout check skipped", exc_info=True)
        return None
    if root is not None:
        logger.warning(
            "Gateway code is running from git work tree %s. Do not fetch-and-rebase, "
            "checkout, switch, pull or reset in it while the gateway runs: its MCP "
            "backends would load mixed old and new code. Make a worktree "
            "(git worktree add) for development instead.",
            root,
        )
    return root
