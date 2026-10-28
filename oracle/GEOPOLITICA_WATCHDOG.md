# Oracle watchdog for Geopolitica

GitHub Actions continues to run every 30 minutes (maximum job runtime: 20 minutes).
Oracle checks the feed every 10 minutes and dispatches the existing workflow only if
the last successful publication is over 60 minutes old. A 40-minute cooldown prevents
repeated dispatches, and active GitHub runs are checked before dispatch.

## Install on Oracle (requires shell access)

Clone or update the repository at /home/ubuntu/Radio-Romanii-Italia.
Set up a GitHub fine-grained token with Actions: Read and write permissions for
the Radio-Romanii-Italia repository; store it only on Oracle, never in Git.

sudo install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/.local/state/rdi-geopolitica-watchdog
sudo install -m 600 -o root -g root /dev/null /etc/rdi-geopolitica-watchdog.env
sudo nano /etc/rdi-geopolitica-watchdog.env

Add this line:
RDI_GITHUB_TOKEN=YOUR_TOKEN

Then run:
sudo cp oracle/geopolitica-watchdog.service /etc/systemd/system/
sudo cp oracle/geopolitica-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now geopolitica-watchdog.timer
sudo systemctl start geopolitica-watchdog.service
sudo journalctl -u geopolitica-watchdog.service -n 25 --no-pager
systemctl list-timers geopolitica-watchdog.timer --no-pager

Do not paste token values into chat or logs.
The service only reads the JSON feed and triggers the existing workflow; it does not
touch the radio player, database, or any other Oracle service.
