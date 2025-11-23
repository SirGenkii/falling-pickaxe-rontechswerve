#!/bin/bash

### === CONFIG === ###
DISPLAY_ID=:99
RESOLUTION=1080x1920
FRAMERATE=30
BITRATE=4500k
AUDIO_SOURCE=default
STREAM_URL="rtmp://a.rtmp.youtube.com/live2"
STREAM_KEY_FILE=".stream_key"
MUSIC_DIR="./obs_bg_musiques"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

### === INSTALL DEPENDENCIES (Debian/Ubuntu) === ###
echo "> Checking/installing ffmpeg, xvfb, pulseaudio, sox..."
sudo apt update && sudo apt install -y ffmpeg xvfb pulseaudio sox

if [ ! -f "$SCRIPT_DIR/$STREAM_KEY_FILE" ]; then
  echo "❌ Stream key file '$STREAM_KEY_FILE' not found in $SCRIPT_DIR. Please create it with your YouTube stream key."
  exit 1
fi
STREAM_KEY=$(cat "$SCRIPT_DIR/$STREAM_KEY_FILE")

### === LAUNCH Xvfb IF NOT RUNNING === ###
if ! pgrep -f "Xvfb $DISPLAY_ID" > /dev/null; then
  echo "> Starting Xvfb on $DISPLAY_ID..."
  Xvfb $DISPLAY_ID -screen 0 ${RESOLUTION}x24 &
  sleep 2
else
  echo "> Xvfb already running on $DISPLAY_ID"
fi
export DISPLAY=$DISPLAY_ID

### === PLAY BACKGROUND MUSIC === ###
if [ -d "$SCRIPT_DIR/$MUSIC_DIR" ]; then
  echo "> Playing music from $MUSIC_DIR in loop..."
  find "$SCRIPT_DIR/$MUSIC_DIR" -type f -name '*.mp3' | sort -R | xargs play -q repeat 999 &
else
  echo "⚠️ Music directory '$MUSIC_DIR' not found. Skipping music playback."
fi

### === WAIT BEFORE STARTING STREAM === ###
echo "> Waiting for virtual display to be ready..."
sleep 5

### === START FFMPEG STREAM === ###
echo "> Starting stream via FFmpeg..."
ffmpeg \
  -f x11grab -s $RESOLUTION -r $FRAMERATE -i $DISPLAY \
  -f pulse -i $AUDIO_SOURCE \
  -c:v libx264 -preset veryfast -b:v $BITRATE -maxrate $BITRATE -bufsize 2M \
  -c:a aac -b:a 128k \
  -f flv "$STREAM_URL/$STREAM_KEY" &

### === LAUNCH FALLING PICKAXE === ###
echo "> Launching Falling Pickaxe..."
cd "$SCRIPT_DIR"
DISPLAY=$DISPLAY_ID python3 falling_pickaxe.py

### === NOTES === ###
# - This script launches the stream, music, and the game automatically
# - Music loops randomly from ./obs_bg_musiques
# - To stop: Ctrl+C or kill ffmpeg, play, and python3 processes
