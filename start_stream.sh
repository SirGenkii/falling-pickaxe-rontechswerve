#!/bin/bash

### === CONFIG === ###
DISPLAY_ID=:99
RESOLUTION=1080x1920x24
AUDIO_SOURCE=default   # PulseAudio source ("pactl list short sources" to list)
STREAM_URL="rtmp://a.rtmp.youtube.com/live2"
STREAM_KEY_FILE=".stream_key"  # expected at root of repo, ignored by git

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
HTML_OVERLAY="$SCRIPT_DIR/obs_scenes/superchat.html"
MUSIC_DIR="$SCRIPT_DIR/obs_bg_musiques"

if [ ! -f "$SCRIPT_DIR/$STREAM_KEY_FILE" ]; then
  echo "❌ Stream key file '$STREAM_KEY_FILE' not found in $SCRIPT_DIR. Please create it with your YouTube stream key."
  exit 1
fi
STREAM_KEY=$(cat "$SCRIPT_DIR/$STREAM_KEY_FILE")

### === CHECK DEPENDENCIES === ###
REQUIRED=(obs xvfb pulseaudio)
echo "> Checking required packages..."
for pkg in "${REQUIRED[@]}"; do
  if ! command -v "$pkg" &> /dev/null; then
    echo "❌ Missing dependency: $pkg. Please install it before running this script."
    exit 1
  fi
done

### === LAUNCH VIRTUAL DISPLAY === ###
echo "> Starting Xvfb..."
Xvfb $DISPLAY_ID -screen 0 $RESOLUTION &
sleep 2
export DISPLAY=$DISPLAY_ID

### === SETUP OBS CONFIG === ###
CONFIG_DIR="$HOME/.config/obs-studio"
PROFILE_NAME="autostream"
SCENE_COLLECTION="scene_autostream"

if [ ! -d "$CONFIG_DIR" ]; then
  echo "> First-time setup detected: generating OBS config."
  mkdir -p "$CONFIG_DIR"
  echo "⚠️ Please create the scene '$SCENE_COLLECTION' with the proper sources manually first on a GUI machine and copy the config here."
  exit 1
fi

### === LAUNCH OBS HEADLESS === ###
echo "> Launching OBS with stream key..."
obs \
  --profile "$PROFILE_NAME" \
  --collection "$SCENE_COLLECTION" \
  --startstreaming \
  --stream "" "$STREAM_URL/$STREAM_KEY" \
  --minimize-to-tray &

### === FINAL === ###
echo "> Streaming started with resolution $RESOLUTION using profile '$PROFILE_NAME'"
echo "> Stream key loaded from '$STREAM_KEY_FILE'."

echo "> To stop streaming: pkill obs && pkill Xvfb"

### === NOTES === ###
# 1. You must first prepare a scene named '$OBS_SCENE' on your local OBS:
#    - Add a Window Capture of falling-pickaxe (can be replaced by screen capture if needed)
#    - Add a Browser Source pointing to:
#        file://$HTML_OVERLAY
#    - Add VLC or Media Source pointing to:
#        $MUSIC_DIR
#
# 1.1 INSTALL : 
# sudo apt update
# sudo apt install -y obs-studio xvfb pulseaudio
#
# 1.2 Check audio
# pulseaudio --check || pulseaudio --start
#
# 2. Then copy your local ~/.config/obs-studio/ to this server.
#    rsync -av ~/.config/obs-studio/ user@server:/home/youruser/.config/obs-studio/
#
# 3. To stop streaming:
#    pkill obs
#    pkill Xvfb


