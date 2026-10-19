# Radio Românii din Italia → YouTube Live (Oracle)

This is a **separate** FFmpeg relay: it reads the existing public AzuraCast MP3 stream and sends a 1280×720 blue still-video plus stereo AAC audio to YouTube RTMP. It does **not** change AzuraCast or the radio website.

## First-time setup (on Oracle, SSH as ubuntu)

```bash
git clone https://github.com/ionut290/Radio-Romanii-Italia.git
cd Radio-Romanii-Italia
sudo bash youtube-live/setup.sh
```

If you already have a checkout, use `git pull` instead of cloning. The installer asks for the YouTube **stream key** with hidden input. Never send the key to chat, GitHub, or screenshots.

Manage the relay:

```bash
sudo systemctl status radio-youtube.service
sudo journalctl -u radio-youtube.service -f
sudo systemctl restart radio-youtube.service
sudo systemctl stop radio-youtube.service
```

On YouTube Studio, create a live stream, configure its visibility, and check the incoming preview. You may need to click **Go live** manually; streaming 24/7 also depends on YouTube policies, connection stability, resources and music licensing. The relay automatically reconnects after errors or reboot.

The service uses H.264 / AAC and sends about 1.33 Mbps outbound; confirm Oracle network capacity and costs. It uses CPU video encoding, so monitor load with `top`. Do not broadcast songs you lack rights to stream on YouTube.

To change keys, rerun the installer, then `sudo systemctl restart radio-youtube.service`. Secrets stay in root-only `/etc/radio-youtube/relay.env` and never go into GitHub.
