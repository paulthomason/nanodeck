#!/usr/bin/env python3

import time
import random
from datetime import datetime
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.lcd.device import st7735
from PIL import ImageFont, ImageDraw, Image

# --- Display Configuration ---
RST_PIN = 27  # GPIO pin connected to the RST (Reset) line 
DC_PIN = 25   # GPIO pin connected to the DC (Data/Command) line 

LCD_WIDTH = 128
LCD_HEIGHT = 128

serial = spi(port=0, device=0, cs_high=False,
             gpio_DC=DC_PIN, gpio_RST=RST_PIN,
             speed_hz=16000000)

device = st7735(serial, width=LCD_WIDTH, height=LCD_HEIGHT, h_offset=2, v_offset=1)

# Load fonts for game text
try:
    font_game = ImageFont.truetype("DejaVuSansMono.ttf", 10)
    font_score = ImageFont.truetype("DejaVuSansMono.ttf", 8)
    font_gameover = ImageFont.truetype("DejaVuSansMono.ttf", 14)
except IOError:
    font_game = ImageFont.load_default()
    font_score = ImageFont.load_default()
    font_gameover = ImageFont.load_default()

# --- GPIO Configuration for Buttons and Joystick ---
GPIO.setmode(GPIO.BCM) # Use BCM numbering

BUTTON_PINS = {
    "KEY1": 21,  # KEY1 GPIO 
    "KEY2": 20,  # KEY2 GPIO 
    "KEY3": 16,  # KEY3 GPIO 
    "JOY_UP": 6, # Upward direction of the Joystick 
    "JOY_DOWN": 19, # Downward direction of the Joystick 
    "JOY_LEFT": 5, # Left direction of the Joystick 
    "JOY_RIGHT": 26, # Right direction of the Joystick 
    "JOY_PRESS": 13 # Press the Joystick 
}

# Set up each button pin as an input with a pull-up resistor
for pin_name, pin_num in BUTTON_PINS.items():
    GPIO.setup(pin_num, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Buttons typically pull low when pressed

# --- Game Constants ---
SNAKE_BLOCK_SIZE = 4 # Size of each snake segment and food item in pixels
GAME_AREA_WIDTH = LCD_WIDTH // SNAKE_BLOCK_SIZE
GAME_AREA_HEIGHT = LCD_HEIGHT // SNAKE_BLOCK_SIZE 
SNAKE_COLOR = "lime"
FOOD_COLOR = "red"
BG_COLOR = "black"
INITIAL_SPEED = 0.25 # Seconds per frame (higher value = slower game)
SPEED_INCREMENT = 0.01 # How much speed increases per food eaten
SCORE_INCREMENT = 10

# --- Game State Variables ---
snake = [] # List of (x, y) tuples for snake segments
food = (0, 0) # (x, y) tuple for food position
direction = "RIGHT" # Current direction of the snake
score = 0
game_over = False
game_speed = INITIAL_SPEED # Current delay between snake moves
last_direction_change_time = 0 # To prevent immediate 180-degree turns and fast changes

# --- Callback for Restarting Game ---
# This function is triggered by KEY1 or JOY_PRESS when the game is over
last_event_time = {name: 0 for name in BUTTON_PINS.items()} # To debounce restart
def restart_game_callback(channel):
    global game_over, snake, food, direction, score, game_speed, last_direction_change_time
    pin_name = next((name for name, num in BUTTON_PINS.items() if num == channel), f"Pin {channel}")

    current_time = time.time()
    # Simple debounce for restart buttons
    if current_time - last_event_time[pin_name] < 0.3: # Minimum 300ms between restarts
        return

    if GPIO.input(channel) == GPIO.LOW: # Only react on button press (falling edge)
        if game_over:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Restarting game!")
            # Reset all game state variables to initial values
            snake = [(GAME_AREA_WIDTH // 2, GAME_AREA_HEIGHT // 2)] # Start in middle of screen
            direction = "RIGHT"
            score = 0
            game_speed = INITIAL_SPEED
            food = generate_food_position(snake) # Generate new food
            game_over = False
            last_direction_change_time = 0 # Reset this too

    last_event_time[pin_name] = current_time # Update last event time for debounce

# Assign restart callback to KEY1 and JOY_PRESS
GPIO.add_event_detect(BUTTON_PINS["KEY1"], GPIO.FALLING, callback=restart_game_callback, bouncetime=200)
GPIO.add_event_detect(BUTTON_PINS["JOY_PRESS"], GPIO.FALLING, callback=restart_game_callback, bouncetime=200)

# --- Game Logic Helper Functions ---

# Generates a random position for food that doesn't overlap with the snake's body
def generate_food_position(snake_body):
    while True:
        fx = random.randint(0, GAME_AREA_WIDTH - 1)
        fy = random.randint(0, GAME_AREA_HEIGHT - 1)
        if (fx, fy) not in snake_body: # Ensure food doesn't spawn on the snake
            return (fx, fy)

# Draws all game elements onto the display canvas
def draw_game_elements(draw_obj, snake_body, food_pos, current_score, game_status):
    # Draw food item
    draw_obj.rectangle(
        (food_pos[0] * SNAKE_BLOCK_SIZE, food_pos[1] * SNAKE_BLOCK_SIZE,
         (food_pos[0] + 1) * SNAKE_BLOCK_SIZE -1, (food_pos[1] + 1) * SNAKE_BLOCK_SIZE -1),
        fill=FOOD_COLOR
    )

    # Draw snake segments
    for i, segment in enumerate(snake_body):
        color = SNAKE_COLOR if i > 0 else "white" # Head is white, body is SNAKE_COLOR
        draw_obj.rectangle(
            (segment[0] * SNAKE_BLOCK_SIZE, segment[1] * SNAKE_BLOCK_SIZE,
             (segment[0] + 1) * SNAKE_BLOCK_SIZE -1, (segment[1] + 1) * SNAKE_BLOCK_SIZE -1),
            fill=color
        )
    
    # Draw current score on screen
    draw_obj.text((3, 3), f"Score: {current_score}", fill="white", font=font_score)

    # If game is over, draw the "Game Over!" screen
    if game_status:
        # Create a semi-transparent black overlay for the "Game Over" message
        overlay = Image.new('RGBA', device.size, (0, 0, 0, 128)) 
        overlay_draw = ImageDraw.Draw(overlay)
        
        text_go = "GAME OVER!"
        text_score = f"Final Score: {current_score}"
        restart_msg = "Press KEY1/JOY_PRESS to restart"
        
        # --- CORRECTED LINES FOR TEXT DIMENSIONS ---
        # Get width using font.getlength()
        text_go_width = font_gameover.getlength(text_go)
        text_score_width = font_game.getlength(text_score)
        restart_msg_width = font_score.getlength(restart_msg)
        
        # Get height using font.getbbox() - getbbox returns (left, top, right, bottom)
        # So height is bottom - top
        text_go_height = font_gameover.getbbox(text_go)[3] - font_gameover.getbbox(text_go)[1]
        text_score_height = font_game.getbbox(text_score)[3] - font_gameover.getbbox(text_go)[1] # Re-using top/bottom for simplicity
        restart_msg_height = font_score.getbbox(restart_msg)[3] - font_score.getbbox(restart_msg)[1]
        # --- END CORRECTED LINES ---
        
        # Center Game Over text using calculated dimensions
        overlay_draw.text(((LCD_WIDTH - text_go_width) // 2, (LCD_HEIGHT - text_go_height) // 2 - 10),
                           text_go, fill="red", font=font_gameover)
        overlay_draw.text(((LCD_WIDTH - text_score_width) // 2, (LCD_HEIGHT - text_score_height) // 2 + 10),
                           text_score, fill="yellow", font=font_game)
        overlay_draw.text(((LCD_WIDTH - restart_msg_width) // 2, (LCD_HEIGHT - restart_msg_height) // 2 + 30),
                           restart_msg, fill="white", font=font_score)
        
        # Composite the overlay onto the main display
        device.display(Image.alpha_composite(Image.new('RGBA', device.size, (0,0,0,0)), overlay))


print("Welcome to Snake on Waveshare HAT! Use joystick to play. KEY1/JOY_PRESS to restart.")
print("Press Ctrl+C to exit.")

# --- Main Game Loop ---
try:
    # Initialize game state for the very first run
    snake = [(GAME_AREA_WIDTH // 2, GAME_AREA_HEIGHT // 2)]
    food = generate_food_position(snake)
    last_move_time = time.time() # Tracks when the snake last moved

    while True:
        # Only process game logic if the game is not over
        if not game_over:
            current_time = time.time()

            # --- Handle Joystick Input (change snake direction) ---
            # Introduce a small delay for direction changes to prevent super fast turns
            if current_time - last_direction_change_time > 0.1: 
                if GPIO.input(BUTTON_PINS["JOY_UP"]) == GPIO.LOW and direction != "DOWN":
                    direction = "UP"
                    last_direction_change_time = current_time
                elif GPIO.input(BUTTON_PINS["JOY_DOWN"]) == GPIO.LOW and direction != "UP":
                    direction = "DOWN"
                    last_direction_change_time = current_time
                elif GPIO.input(BUTTON_PINS["JOY_LEFT"]) == GPIO.LOW and direction != "RIGHT":
                    direction = "LEFT"
                    last_direction_change_time = current_time
                elif GPIO.input(BUTTON_PINS["JOY_RIGHT"]) == GPIO.LOW and direction != "LEFT":
                    direction = "RIGHT"
                    last_direction_change_time = current_time

            # --- Game Tick (Move Snake) ---
            # Move the snake only if enough time has passed based on game_speed
            if current_time - last_move_time > game_speed:
                last_move_time = current_time

                # Determine the new head position
                head_x, head_y = snake[0]
                new_head = (head_x, head_y)

                if direction == "UP":
                    new_head = (head_x, head_y - 1)
                elif direction == "DOWN":
                    new_head = (head_x, head_y + 1)
                elif direction == "LEFT":
                    new_head = (head_x - 1, head_y)
                elif direction == "RIGHT":
                    new_head = (head_x + 1, head_y)

                # --- Check for Collisions ---
                # 1. Wall collision
                if not (0 <= new_head[0] < GAME_AREA_WIDTH and 0 <= new_head[1] < GAME_AREA_HEIGHT):
                    game_over = True
                # 2. Self-collision (check new_head against body, excluding tail if not growing)
                # The 'len(snake) > 1' check is important to prevent a 1-block snake from "colliding" with itself
                elif new_head in snake and (len(snake) > 1 or new_head != snake[-1]): 
                    game_over = True
                else:
                    snake.insert(0, new_head) # Add the new head to the front of the snake

                    # --- Check for Food Consumption ---
                    if new_head == food:
                        score += SCORE_INCREMENT # Increase score
                        game_speed = max(0.05, game_speed - SPEED_INCREMENT) # Increase speed (min cap 0.05s)
                        food = generate_food_position(snake) # Generate new food position
                    else:
                        snake.pop() # Remove the tail segment if snake didn't eat (normal movement)

        # --- Drawing ---
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline=BG_COLOR, fill=BG_COLOR) # Clear screen with background color
            draw_game_elements(draw, snake, food, score, game_over) # Draw all game components

        # Small sleep to ensure consistent frame rate and prevent CPU hogging
        time.sleep(0.01) # This determines the display update rate, separate from game_speed

except KeyboardInterrupt:
    print("\nExiting Snake game.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
finally:
    print("Cleaning up display and GPIO resources...")
    device.cleanup() # Cleans up luma.lcd display resources
    GPIO.cleanup()   # Cleans up RPi.GPIO pins
    print("Cleanup complete.")
