# YouTube visual capture — full website

Experimental visual broadcasting mode. **Not enabled by default.** The current working blue-background relay keeps running.

This uses Xvfb + Chromium to show the actual public homepage, FFmpeg to capture the visible viewport, and AzuraCast as the sole audio source. It scrolls the homepage, refreshes news and rotates to the public /comunitate.html page before returning to the homepage. A video of a website is not interactive: viewers must visit the website to post or comment.

## Install on the Oracle host

```bash
cd ~/Radio-Romanii-Italia
git pull --ff-only
sudo bash youtube-live/install-visual.sh
```

The package `chromium-browser` on Ubuntu 22.04 often uses Snap (install size/resource requirements depend on OS). This may fail on constrained Oracle ARM instances, so test before switching. Keep 1.5GB free and monitor `df -h /`, `free -h`, `top`.

## Test and switch (only after installation succeeds)

**Do not start both services at once.** To switch temporarily:
```bash
sudo systemctl stop radio-youtube.service
sudo systemctl start radio-youtube-visual.service
sudo systemctl is-active radio-youtube-visual.service
ps -C ffmpeg -o pid,etime,%cpu --no-headers
```

Observe YouTube Studio quality for a few minutes. If it fails, roll back immediately:
```bash
sudo systemctl stop radio-youtube-visual.service
sudo systemctl start radio-youtube.service
```

To enable visual mode on reboot only after stable testing:
```bash
sudo systemctl disable radio-youtube.service
sudo systemctl enable radio-youtube-visual.service
```

For privacy, only show public web content. Check moderation and ensure no private messages, user profiles, or browser admin sessions appear in the capture. For YouTube, secure music and image rights before public streaming.
