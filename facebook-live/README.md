# Radio Românii din Italia → Facebook Live

**Prepared, not active.** These files do not start or enable a Facebook Live
and do not alter the active YouTube, radio, or AzuraCast services.

## Requirements before activation

- Manage the intended Facebook Page. As of October 2026, Live Producer
  generally requires a Facebook account aged 60+ days and 100+ Page followers.
- Open [Facebook Live Producer](https://www.facebook.com/live/producer/),
  choose the Page and **Streaming software**, and obtain the actual RTMPS
  server URL and stream key. Choose a persistent key only if Facebook offers it.
- Confirm that your music, podcasts and advertising can be broadcast on Facebook.
- Check Oracle instance CPU and outgoing transfer: this is a *second video
  encoder*, although it reuses the same 1280×720 Xvfb display (:92).

## Architecture

Oracle AzuraCast audio + current RDI Xvfb display (:92) → independent FFmpeg
H.264 720p 15fps / AAC 128 kbps → Facebook RTMPS.

The YouTube FFmpeg process, browser and stream key are never modified.
There is no second Chromium instance. Facebook's separate FFmpeg encoder
will add server load, so verify performance during a short test.

## Installation (Oracle, only when ready)

Use your existing private SSH connection to the Oracle server. In the
Radio-Romanii-Italia repository checkout, pull the latest code, then:

    sudo bash facebook-live/setup.sh

The installer asks for your RTMPS server and secret stream key in the
terminal; it stores them root-only in /etc/radio-facebook/relay.env.
**Never paste your key into ChatGPT, public GitHub, logs, or screenshots.**
The installer does not start Facebook and does not enable the service.

Prepare the Live in Facebook Live Producer, then explicitly start:

    sudo systemctl start rdi-facebook.service

Check the Facebook preview and press **Go Live** there if required. Stop
only Facebook with:

    sudo systemctl stop rdi-facebook.service

Inspect without sharing secrets:

    sudo systemctl status rdi-facebook.service
    sudo journalctl -u rdi-facebook.service -n 20 --no-pager

The relay attempts a new encoder session after ~7h50m, but **Facebook
ends each Live after at most 8 hours**. Restarting FFmpeg with the same key
does not guarantee a new Facebook Live will be created/started. A Page
operator or an appropriately authorized platform integration may need
to prepare each new Facebook broadcast. **24/7 on Facebook is therefore
not guaranteed** until a compliant restart workflow has been verified.

TikTok is not connected yet.
