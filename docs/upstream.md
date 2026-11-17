# Upstream maintenance

This repository derives from [Keebart/zmk-config](https://github.com/Keebart/zmk-config),
branch `main`. GitHub currently reports `fork: false`, so the parent relationship
is tracked with a Git remote instead of GitHub's fork-sync button. The shared
history and the previous merge `da782c7` establish this relationship.

Check periodically, and before changing firmware dependencies:

```sh
# Once per clone, if the remote does not already exist:
git remote add upstream https://github.com/Keebart/zmk-config.git
git fetch origin
git fetch upstream
git rev-list --left-right --count origin/main...upstream/main
git log --oneline origin/main..upstream/main
git diff origin/main...upstream/main
```

The second count is the number of upstream commits missing from the fork's main
branch. A nonzero first count is expected: this repository contains a custom
keymap and build matrix.

With a clean working tree, merge upstream into `main`, preserving the custom
keymap and build targets when resolving conflicts. Review changes to board
definitions, ZMK versions and configuration defaults, then push and check the
firmware build. Merge the updated `main` into active feature branches as well.
Do not replace `main` with upstream or force-push to synchronize this repository.

On 2026-11-17 the missing commits were `1354d3f` (five-minute idle timeout) and
`98c5a11` (encoder triggers per rotation). Neither changes the custom keymap or
the firmware dependency versions.
