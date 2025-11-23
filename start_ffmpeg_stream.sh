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

### === INSTALL DEPENDENCIES === ###
echo "> Installing dependencies..."
sudo apt update && sudo apt install -y ffmpeg xvfb pulseaudio sox xdotool

### === LOAD STREAM KEY === ###
if [ ! -f "$SCRIPT_DIR/$STREAM_KEY_FILE" ]; then
  echo "❌ Stream key file '$STREAM_KEY_FILE' not found in $SCRIPT_DIR."
  exit 1
fi
STREAM_KEY=$(cat "$SCRIPT_DIR/$STREAM_KEY_FILE")

### === LAUNCH VIRTUAL DISPLAY === ###
pkill -f "Xvfb $DISPLAY_ID" 2>/dev/null
sleep 1
Xvfb $DISPLAY_ID -screen 0 ${RESOLUTION}x24 &
sleep 2
export DISPLAY=$DISPLAY_ID

### === START MUSIC === ###
if [ -d "$SCRIPT_DIR/$MUSIC_DIR" ]; then
  echo "> Playing background music..."
  ( while true; do find "$SCRIPT_DIR/$MUSIC_DIR" -type f -iname '*.mp3' | shuf | xargs play; done ) &
else
  echo "⚠️  No music folder found."
fi

### === START GAME === ###
echo "> Launching game..."
cd "$SCRIPT_DIR"
DISPLAY=$DISPLAY_ID python3 falling_pickaxe.py &
sleep 5

### === DETECT ACTIVE WINDOW === ###
WINDOW_ID=$(xdotool search --onlyvisible --limit 1 --class "python3")
if [ -z "$WINDOW_ID" ]; then
  echo "❌ No game window found to stream."
  exit 1
fi

### === START STREAM === ###
echo "> Starting stream..."
ffmpeg \
  -f x11grab -draw_mouse 0 -r $FRAMERATE -s $RESOLUTION -i $DISPLAY \
  -f pulse -i $AUDIO_SOURCE \
  -c:v libx264 -preset veryfast -b:v $BITRATE -maxrate $BITRATE -bufsize 2M \
  -c:a aac -b:a 128k \
  -f flv "$STREAM_URL/$STREAM_KEY"
