#!/bin/bash

### === CONFIG === ###
DISPLAY_ID=:99
RESOLUTION=1080x1920
FRAMERATE=30
BITRATE=4500k
AUDIO_SOURCE=default
STREAM_URL="rtmp://a.rtmp.youtube.com/live2"
STREAM_KEY_FILE=".stream_key"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

### === INSTALL DEPENDENCIES (Debian/Ubuntu) === ###
echo "> Checking/installing ffmpeg, xvfb, pulseaudio..."
sudo apt update && sudo apt install -y ffmpeg xvfb pulseaudio

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
# - This script launches both the stream and the game automatically
# - Make sure your game window fits the specified resolution
# - To stop: Ctrl+C or kill ffmpeg and python3 processes
