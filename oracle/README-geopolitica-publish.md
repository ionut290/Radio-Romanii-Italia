# Oracle Geopolitica publisher (staged, NOT automatically enabled)

This is separate from the existing `rdi-geopolitica.timer` used for radio audio.
It runs the existing Python news collector and pushes ONLY
`data/geopolitica-news.json` to GitHub Pages' main branch.

## Safety prerequisites

1. Ensure `/home/ubuntu/rdi-geopolitica` is a Git checkout on main.
2. Configure **write access to GitHub** for the `ubuntu` user, preferably a narrowly scoped deploy credential. Do not place secrets in the repository or command output.
3. Check `git status --short` first. **A previously observed local change to data/geopolitica-news.json must be reconciled manually before enabling**. Never blindly discard it.
4. Do not enable the Oracle timer while the GitHub Actions scheduled collector is active: both use the same 15-minute schedule and can race. First run a controlled manual test, then switch one scheduler off and the other on.

## Install (after prerequisites)

```bash
cd /home/ubuntu/rdi-geopolitica
git status --short
sudo install -m 0644 oracle/rdi-geopolitica-publish.service /etc/systemd/system/
sudo install -m 0644 oracle/rdi-geopolitica-publish.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start rdi-geopolitica-publish.service
sudo systemctl show rdi-geopolitica-publish.service -p Result -p ExecMainStatus
sudo journalctl -u rdi-geopolitica-publish.service -n 40 --no-pager
```

Verify the resulting JSON on GitHub and on the public site. Only after success, disable the **schedule** in `.github/workflows/geopolitica.yml` (preserve manual dispatch), then enable:

```bash
sudo systemctl enable --now rdi-geopolitica-publish.timer
systemctl list-timers rdi-geopolitica-publish.timer --no-pager
```

Rollback: `sudo systemctl disable --now rdi-geopolitica-publish.timer`, restore GitHub Actions schedule. Existing radio timer is untouched.
