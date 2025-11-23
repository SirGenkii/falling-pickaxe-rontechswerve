import time
import pygame
import pymunk
import pymunk.pygame_util
from youtube import (
    get_active_live_stream,
    get_live_stream,
    get_live_chat_id_for_channel,
    get_new_live_chat_messages,
    get_subscriber_count,
    validate_live_stream_id,
)
from config import config
from atlas import create_texture_atlas
from pathlib import Path
from chunk import get_block, clean_chunks, delete_block, chunks
from constants import BLOCK_SCALE_FACTOR, BLOCK_SIZE, CHUNK_HEIGHT, CHUNK_WIDTH, INTERNAL_HEIGHT, INTERNAL_WIDTH, FRAMERATE
from pickaxe import Pickaxe
from camera import Camera
from sound import SoundManager
from tnt import Tnt, MegaTnt
import asyncio
import threading
import random
from hud import Hud

# Track key states
key_t_pressed = False
key_m_pressed = False

#
live_stream = None
live_chat_id = None
subscribers = None

if config["CHAT_CONTROL"] == True:
    print("Checking for active live stream on configured channel")
    channel_id = config.get("CHANNEL_ID")
    if channel_id:
        live_stream = get_active_live_stream(channel_id)

    if live_stream is None and config.get("LIVESTREAM_ID"):
        print("No active live stream found via channel search. Checking fallback livestream ID...")
        stream_id = validate_live_stream_id(config["LIVESTREAM_ID"])
        if stream_id:
            live_stream = get_live_stream(stream_id)

    if live_stream is None:
        print("No active live stream found. App will run without it.")
    else:
        print("Live stream found:", live_stream["snippet"]["title"])

    # get chat id from live stream
    if live_stream is not None:
        live_chat_id = live_stream.get("liveStreamingDetails", {}).get("activeLiveChatId")
        if live_chat_id is None and channel_id:
            print("Fetching live chat ID from channel...")
            live_chat_id = get_live_chat_id_for_channel(channel_id)

    if live_chat_id is None:
        print("No live chat ID found. App will run without it.")
    else:
        print("Live chat ID found:", live_chat_id)

    # get subscribers count
    if(config["CHANNEL_ID"] is not None and config["CHANNEL_ID"] != ""):
        print("Fetching subscribers count...")
        subscribers = get_subscriber_count(config["CHANNEL_ID"])

    if subscribers is None:
        print("No subscribers count found. App will run without it.")
    else:
        print("Subscribers count found:", subscribers)

# Queues for chat
tnt_queue = []
tnt_superchat_queue = []
fast_slow_queue = []
big_queue = []
pickaxe_queue = []
mega_tnt_queue = []

async def handle_youtube_poll():
    global subscribers # Use global to modify the variable

    if subscribers is not None:
        new_subscribers = get_subscriber_count(config["CHANNEL_ID"])
        if new_subscribers is not None and new_subscribers > subscribers:
            mega_tnt_queue.append("New Subscriber") # Add to mega tnt queue
            subscribers = new_subscribers # Update subscriber count

    new_messages = get_new_live_chat_messages(live_chat_id)

    for message in new_messages:
        author = message["author"]
        text = message["message"] or ""
        author_id = message.get("author_channel_id") or author
        profile_image_url = message.get("profile_image_url")
        is_superchat = message["sc_details"] is not None
        is_supersticker = message["ss_details"] is not None

        text_lower = text.lower()
        chat_payload = {
            "author_id": author_id,
            "display_name": author,
            "message": text,
            "profile_image_url": profile_image_url,
        }

    

        # Check for MegaTNT keyword
        if "megatnt" in text_lower or "mega" in text_lower:
            mega_tnt_queue.append({**chat_payload, "highlight": "megatnt"})
            print(f"Added {author} to MegaTNT queue (keyword)")

        elif "tnt" in text_lower:
        # Every chat message spawns at least one TNT with metadata for the overlay
            tnt_queue.append({**chat_payload, "highlight": "tnt" if "tnt" in text_lower else None})
            print(f"Queued TNT for chat message from {author}")

        # Check for Superchat/Supersticker (add to mega tnt queue for 10x MegaTNT)
        if is_superchat or is_supersticker:
            tnt_superchat_queue.append({**chat_payload, "highlight": "megatnt"})
            print(f"Added {author} to Superchat MegaTNT queue")

        if "fast" in text_lower and author_id not in [entry["author_id"] for entry in fast_slow_queue]:
            fast_slow_queue.append({"author_id": author_id, "display_name": author, "choice": "Fast"})
            print(f"Added {author} to Fast/Slow queue (Fast)")
        elif "slow" in text_lower and author_id not in [entry["author_id"] for entry in fast_slow_queue]:
            fast_slow_queue.append({"author_id": author_id, "display_name": author, "choice": "Slow"})
            print(f"Added {author} to Fast/Slow queue (Slow)")

        if "big" in text_lower and author_id not in [entry["author_id"] for entry in big_queue]:
            big_queue.append({"author_id": author_id, "display_name": author})
            print(f"Added {author} to Big queue")

        # Check for pickaxe commands (add author and pickaxe type to pickaxe_queue)
        if "wood" in text_lower:
            if author_id not in [entry["author_id"] for entry in pickaxe_queue]:
                pickaxe_queue.append({"author_id": author_id, "display_name": author, "pickaxe_type": "wooden_pickaxe"})
                print(f"Added {author} to Pickaxe queue (wooden_pickaxe)")
        elif "stone" in text_lower:
            if author_id not in [entry["author_id"] for entry in pickaxe_queue]:
                pickaxe_queue.append({"author_id": author_id, "display_name": author, "pickaxe_type": "stone_pickaxe"})
                print(f"Added {author} to Pickaxe queue (stone_pickaxe)")
        elif "iron" in text_lower:
            if author_id not in [entry["author_id"] for entry in pickaxe_queue]:
                pickaxe_queue.append({"author_id": author_id, "display_name": author, "pickaxe_type": "iron_pickaxe"})
                print(f"Added {author} to Pickaxe queue (iron_pickaxe)")
        elif "gold" in text_lower:
            if author_id not in [entry["author_id"] for entry in pickaxe_queue]:
                pickaxe_queue.append({"author_id": author_id, "display_name": author, "pickaxe_type": "golden_pickaxe"})
                print(f"Added {author} to Pickaxe queue (golden_pickaxe)")
        elif "diamond" in text_lower:
            if author_id not in [entry["author_id"] for entry in pickaxe_queue]:
                pickaxe_queue.append({"author_id": author_id, "display_name": author, "pickaxe_type": "diamond_pickaxe"})
                print(f"Added {author} to Pickaxe queue (diamond_pickaxe)")
        elif "netherite" in text_lower:
            if author_id not in [entry["author_id"] for entry in pickaxe_queue]:
                pickaxe_queue.append({"author_id": author_id, "display_name": author, "pickaxe_type": "netherite_pickaxe"})
                print(f"Added {author} to Pickaxe queue (netherite_pickaxe)")

    # print the queue counts (optional, for debugging)
    # print(f"Queues: TNT={len(tnt_queue)}, Superchat TNT={len(tnt_superchat_queue)}, Fast/Slow={len(fast_slow_queue)}, Big={len(big_queue)}, Pickaxe={len(pickaxe_queue)}, MegaTNT={len(mega_tnt_queue)}")

def start_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Create a new event loop
asyncio_loop = asyncio.new_event_loop()
# Start it in a daemon thread so it doesn’t block shutdown
threading.Thread(target=start_event_loop, args=(asyncio_loop,), daemon=True).start()

def game():
    window_width = int(INTERNAL_WIDTH / 2)
    window_height = int(INTERNAL_HEIGHT / 2)

    # Initialize pygame
    pygame.init()
    clock = pygame.time.Clock()

    # Pymunk physics
    space = pymunk.Space()
    space.gravity = (0, 1000)  # (x, y) - down is positive y

    # Create a resizable window
    screen_size = (window_width, window_height)
    screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
    pygame.display.set_caption("Falling Pickaxe")
    # set icon
    icon = pygame.image.load(Path(__file__).parent.parent / "src/assets/pickaxe" / "diamond_pickaxe.png")
    pygame.display.set_icon(icon)

    # Create an internal surface with fixed resolution
    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))

    # Load texture atlas
    assets_dir = Path(__file__).parent.parent / "src/assets"
    (texture_atlas, atlas_items) = create_texture_atlas(assets_dir)

    # Load background
    background_image = pygame.image.load(assets_dir / "background.png")
    background_scale_factor = 1.5
    background_width = int(background_image.get_width() * background_scale_factor)
    background_height = int(background_image.get_height() * background_scale_factor)
    background_image = pygame.transform.scale(background_image, (background_width, background_height))

    # Scale the entire texture atlas
    texture_atlas = pygame.transform.scale(texture_atlas,
                                        (texture_atlas.get_width() * BLOCK_SCALE_FACTOR,
                                        texture_atlas.get_height() * BLOCK_SCALE_FACTOR))

    for category in atlas_items:
        for item in atlas_items[category]:
            x, y, w, h = atlas_items[category][item]
            atlas_items[category][item] = (x * BLOCK_SCALE_FACTOR, y * BLOCK_SCALE_FACTOR, w * BLOCK_SCALE_FACTOR, h * BLOCK_SCALE_FACTOR)

    #sounds
    sound_manager = SoundManager()

    sound_manager.load_sound("tnt", assets_dir / "sounds" / "tnt.mp3", 0.3)
    sound_manager.load_sound("stone1", assets_dir / "sounds" / "stone1.wav", 0.5)
    sound_manager.load_sound("stone2", assets_dir / "sounds" / "stone2.wav", 0.5)
    sound_manager.load_sound("stone3", assets_dir / "sounds" / "stone3.wav", 0.5)
    sound_manager.load_sound("stone4", assets_dir / "sounds" / "stone4.wav", 0.5)
    sound_manager.load_sound("grass1", assets_dir / "sounds" / "grass1.wav", 0.1)
    sound_manager.load_sound("grass2", assets_dir / "sounds" / "grass2.wav", 0.1)
    sound_manager.load_sound("grass3", assets_dir / "sounds" / "grass3.wav", 0.1)
    sound_manager.load_sound("grass4", assets_dir / "sounds" / "grass4.wav", 0.1)

    # Pickaxe
    pickaxe = Pickaxe(space, INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2, texture_atlas.subsurface(atlas_items["pickaxe"]["wooden_pickaxe"]), sound_manager)

    # TNT
    last_tnt_spawn = pygame.time.get_ticks()
    tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
    tnt_list = []  # List to keep track of spawned TNT objects

    # Random Pickaxe
    last_random_pickaxe = pygame.time.get_ticks()
    random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])

    # Pickaxe enlargement
    last_enlarge = pygame.time.get_ticks()
    enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])
    enlarge_duration = 1000 * config["PICKAXE_ENLARGE_DURATION_SECONDS"]

    # Fast slow
    fast_slow_active = False
    fast_slow = random.choice(["Fast", "Slow"])
    fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
    last_fast_slow = pygame.time.get_ticks()

    # Camera
    camera = Camera()

    # HUD
    hud = Hud(texture_atlas, atlas_items, position=(32,256), legend_offset=200, leaderboard_offset=400)
    hud.set_pickaxe_name(pickaxe.display_name())

    # Explosions
    explosions = []

    # Youtube
    yt_poll_interval = 1000 * config["YT_POLL_INTERVAL_SECONDS"]
    last_yt_poll = pygame.time.get_ticks()

    # Save progress interval
    save_progress_interval = 1000 * config["SAVE_PROGRESS_INTERVAL_SECONDS"]
    last_save_progress = pygame.time.get_ticks()

    # Youtupe chat queues
    queues_pop_interval = 1000 * config["QUEUES_POP_INTERVAL_SECONDS"]
    last_queues_pop = pygame.time.get_ticks()

    # Main loop
    running = True
    user_quit = False
    while running:
        # ++++++++++++++++++  EVENTS ++++++++++++++++++
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Close window event
                running = False
                user_quit = True
            elif event.type == pygame.VIDEORESIZE:  # Window resize event
                new_width, new_height = event.w, event.h

                # Maintain 9:16 aspect ratio
                if new_width / 9 > new_height / 16:
                    new_width = int(new_height * (9 / 16))
                else:
                    new_height = int(new_width * (16 / 9))

                window_width, window_height = new_width, new_height
                screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)

        # ++++++++++++++++++  UPDATE ++++++++++++++++++
        # Determine which chunks are visible
        # Update physics

        step_speed = 1 / FRAMERATE  # Fixed time step for physics simulation
        if fast_slow_active and fast_slow == "Fast":
            step_speed = 1 / (FRAMERATE / 2)
        elif fast_slow_active and fast_slow == "Slow":
            step_speed = 1 / (FRAMERATE * 2)

        space.step(step_speed)

        start_chunk_y = int(pickaxe.body.position.y // (CHUNK_HEIGHT * BLOCK_SIZE) - 1) - 1
        end_chunk_y = int(pickaxe.body.position.y + INTERNAL_HEIGHT) // (CHUNK_HEIGHT * BLOCK_SIZE)  + 1

        # Update pickaxe
        pickaxe.update()

        # Update camera
        camera.update(pickaxe.body.position.y)

        # ++++++++++++++++++  DRAWING ++++++++++++++++++
        # Clear the internal surface
        screen.fill((0, 0, 0))

        # Fill internal surface with the background
        internal_surface.blit(background_image, ((INTERNAL_WIDTH - background_width) // 2, (INTERNAL_HEIGHT - background_height) // 2))

        # Check if it's time to spawn a new TNT (regular random spawn)
        current_time = pygame.time.get_ticks()
        if (not config["CHAT_CONTROL"] or (not tnt_queue and not tnt_superchat_queue and not mega_tnt_queue)) and current_time - last_tnt_spawn >= tnt_spawn_interval:
             # Example: spawn TNT at position (400, 300) with a given texture
             new_tnt = Tnt(
                 space,
                 pickaxe.body.position.x,
                 pickaxe.body.position.y - 100,
                 texture_atlas,
                 atlas_items,
                 sound_manager,
                 leaderboard=hud,
             )
             tnt_list.append(new_tnt)
             last_tnt_spawn = current_time
             # New random interval for the next TNT spawn
             tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])

        # Check if it's time to change the pickaxe (random)
        if (not config["CHAT_CONTROL"] or not pickaxe_queue) and current_time - last_random_pickaxe >= random_pickaxe_interval:
            pickaxe.random_pickaxe(texture_atlas, atlas_items)
            hud.set_pickaxe_name(pickaxe.display_name())
            last_random_pickaxe = current_time
            # New random interval for the next pickaxe change
            random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])

        # Check if it's time for pickaxe enlargement (random)
        if (not config["CHAT_CONTROL"] or not big_queue) and current_time - last_enlarge >= enlarge_interval:
            pickaxe.enlarge(enlarge_duration)
            last_enlarge = current_time + enlarge_duration
            # New random interval for the next enlargement
            enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])

        # Check if it's time to change speed (random)
        if (not config["CHAT_CONTROL"] or not fast_slow_queue) and current_time - last_fast_slow >= fast_slow_interval and not fast_slow_active:
            # Randomly choose between "fast" and "slow"
            fast_slow = random.choice(["Fast", "Slow"])
            print("Changing speed to:", fast_slow)
            fast_slow_active = True
            last_fast_slow = current_time
            # New random interval for the next fast/slow spawn
            fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
        elif current_time - last_fast_slow >= (1000 * config["FAST_SLOW_DURATION_SECONDS"]) and fast_slow_active:
            fast_slow_active = False
            last_fast_slow = current_time

        # Update all TNTs
        for tnt in tnt_list:
            tnt.update(tnt_list, explosions, camera)

        # Poll Yotutube api
        if live_chat_id is not None and current_time - last_yt_poll >= yt_poll_interval:
            print("Polling YouTube API...")
            last_yt_poll = current_time
            asyncio.run_coroutine_threadsafe(handle_youtube_poll(), asyncio_loop)

        # Process chat queues
        if config["CHAT_CONTROL"] and current_time - last_queues_pop >= queues_pop_interval:
            last_queues_pop = current_time

            # Handle regular TNT from chat command
            if tnt_queue:
                chat_info = tnt_queue.pop(0)
                author = chat_info["display_name"]
                print(f"Spawning TNT for {author} (chat message)")
                new_tnt = Tnt(
                    space,
                    pickaxe.body.position.x,
                    pickaxe.body.position.y - 100,
                    texture_atlas,
                    atlas_items,
                    sound_manager,
                    owner_display_name=author,
                    owner_message=chat_info.get("message"),
                    profile_image_url=chat_info.get("profile_image_url"),
                    owner_id=chat_info.get("author_id"),
                    leaderboard=hud,
                )
                if chat_info.get("highlight"):
                    hud.mark_command_trigger(chat_info["highlight"])
                tnt_list.append(new_tnt)
                last_tnt_spawn = current_time

            # Handle MegaTNT (New Subscriber)
            if mega_tnt_queue:
                author = mega_tnt_queue.pop(0)
                if isinstance(author, dict):
                    display_name = author.get("display_name", "New Subscriber")
                    message = author.get("message")
                    profile_image_url = author.get("profile_image_url")
                    author_id = author.get("author_id")
                    highlight = author.get("highlight")
                else:
                    display_name = author
                    message = None
                    profile_image_url = None
                    author_id = str(author)
                    highlight = "megatnt"

                print(f"Spawning MegaTNT for {display_name} (queue)")
                new_megatnt = MegaTnt(
                    space,
                    pickaxe.body.position.x,
                    pickaxe.body.position.y - 100,
                    texture_atlas,
                    atlas_items,
                    sound_manager,
                    owner_display_name=display_name,
                    owner_message=message,
                    profile_image_url=profile_image_url,
                    owner_id=author_id,
                    leaderboard=hud,
                )
                if highlight:
                    hud.mark_command_trigger(highlight)
                tnt_list.append(new_megatnt)
                last_tnt_spawn = current_time

            # Handle Superchat/Supersticker TNT
            if tnt_superchat_queue:
                chat_info = tnt_superchat_queue.pop(0)
                author = chat_info["display_name"]
                text = chat_info.get("message")
                print(f"Spawning MegaTNTs for {author} (Superchat: {text})")
                last_tnt_spawn = current_time
                hud.mark_command_trigger("megatnt")
                for _ in range(10):
                    new_megatnt = MegaTnt(
                        space,
                        pickaxe.body.position.x,
                        pickaxe.body.position.y - 100,
                        texture_atlas,
                        atlas_items,
                        sound_manager,
                        owner_display_name=author,
                        owner_message=text,
                        profile_image_url=chat_info.get("profile_image_url"),
                        owner_id=chat_info.get("author_id"),
                        leaderboard=hud,
                    )
                    tnt_list.append(new_megatnt)

            # Handle Fast/Slow command
            if fast_slow_queue:
                fast_slow_entry = fast_slow_queue.pop(0)
                author = fast_slow_entry["display_name"]
                q_fast_slow = fast_slow_entry["choice"]
                print(f"Changing speed for {author} to {q_fast_slow}")
                fast_slow_active = True
                last_fast_slow = current_time
                fast_slow = q_fast_slow
                fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
                hud.mark_command_trigger(q_fast_slow.lower())

            # Handle Big pickaxe command
            if big_queue:
                big_entry = big_queue.pop(0)
                author = big_entry["display_name"]
                print(f"Making pickaxe big for {author}")
                pickaxe.enlarge(enlarge_duration)
                last_enlarge = current_time + enlarge_duration
                enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])
                hud.mark_command_trigger("big")

            # Handle Pickaxe type command
            if pickaxe_queue:
                pickaxe_entry = pickaxe_queue.pop(0)
                author = pickaxe_entry["display_name"]
                pickaxe_type = pickaxe_entry["pickaxe_type"]
                print(f"Changing pickaxe for {author} to {pickaxe_type}")
                pickaxe.pickaxe(pickaxe_type, texture_atlas, atlas_items)
                hud.set_pickaxe_name(pickaxe.display_name())
                last_random_pickaxe = current_time
                random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])
                pickaxe_command_map = {
                    "wooden_pickaxe": "wood",
                    "stone_pickaxe": "stone",
                    "iron_pickaxe": "iron",
                    "golden_pickaxe": "gold",
                    "diamond_pickaxe": "diamond",
                    "netherite_pickaxe": "netherite",
                }
                hud.mark_command_trigger(pickaxe_command_map.get(pickaxe_type, pickaxe_type))


        # Delete chunks
        clean_chunks(start_chunk_y)

        # Draw blocks in visible chunks
        for chunk_x in range(-1, 2):
            for chunk_y in range(start_chunk_y, end_chunk_y):
                for y in range(CHUNK_HEIGHT):
                    for x in range(CHUNK_WIDTH):
                        block = get_block(chunk_x, chunk_y, x, y, texture_atlas, atlas_items, space)

                        if block == None:
                            continue

                        block.update(space, hud)
                        block.draw(internal_surface, camera)

        # Draw pickaxe
        pickaxe.draw(internal_surface, camera)

        # Draw TNT
        for tnt in tnt_list:
            tnt.draw(internal_surface, camera)

        # Draw particles
        for explosion in explosions:
            explosion.update()
            explosion.draw(internal_surface, camera)

        # Optionally, remove explosions that have no particles left:
        explosions = [e for e in explosions if e.particles]

        # Draw HUD
        hud.draw(internal_surface, pickaxe.body.position.y, fast_slow_active, fast_slow)

        # Scale internal surface to fit the resized window
        scaled_surface = pygame.transform.smoothscale(internal_surface, (window_width, window_height))
        screen.blit(scaled_surface, (0, 0))

        # Save progress
        if current_time - last_save_progress >= save_progress_interval:
            # Save the game state or progress here
            print("Saving progress...")
            last_save_progress = current_time
            # Save progress to logs folder
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "progress.txt", "a+") as f:
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')} | ")
                f.write(f"Y: {-int(pickaxe.body.position.y // BLOCK_SIZE)} ")
                f.write(f"coal: {hud.amounts['coal']} ")
                f.write(f"iron: {hud.amounts['iron_ingot']} ")
                f.write(f"gold: {hud.amounts['gold_ingot']} ")
                f.write(f"copper: {hud.amounts['copper_ingot']} ")
                f.write(f"redstone: {hud.amounts['redstone']} ")
                f.write(f"lapis: {hud.amounts['lapis_lazuli']} ")
                f.write(f"diamond: {hud.amounts['diamond']} ")
                f.write(f"emerald: {hud.amounts['emerald']} \n")

        # Update the display
        pygame.display.flip()
        clock.tick(FRAMERATE)  # Cap the frame rate

        # Inside the main loop
        keys = pygame.key.get_pressed()

        # Handle TNT spawn (key T)
        if keys[pygame.K_t]:
            if not key_t_pressed:  # Only spawn if the key was not pressed in the previous frame
                new_tnt = Tnt(
                    space,
                    pickaxe.body.position.x,
                    pickaxe.body.position.y - 100,
                    texture_atlas,
                    atlas_items,
                    sound_manager,
                    leaderboard=hud,
                )
                tnt_list.append(new_tnt)
                last_tnt_spawn = current_time
                # New random interval for the next TNT spawn
                tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
            key_t_pressed = True
        else:
            key_t_pressed = False  # Reset the flag when the key is released

        # Handle MegaTNT spawn (key M)
        if keys[pygame.K_m]:
            if not key_m_pressed:  # Only spawn if the key was not pressed in the previous frame
                new_megatnt = MegaTnt(
                    space,
                    pickaxe.body.position.x,
                    pickaxe.body.position.y - 100,
                    texture_atlas,
                    atlas_items,
                    sound_manager,
                    leaderboard=hud,
                )
                tnt_list.append(new_megatnt)
                last_tnt_spawn = current_time
                # New random interval for the next TNT spawn
                tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
            key_m_pressed = True
        else:
            key_m_pressed = False  # Reset the flag when the key is released

    # Quit pygame properly
    pygame.quit()

    # Return exit code: 0 for user quit (close window), 1 for crash/error
    if user_quit:
        import sys
        sys.exit(0)  # Normal exit - user closed window
    else:
        import sys
        sys.exit(1)  # Abnormal exit - game crashed or error

game()