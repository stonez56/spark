import time
import threading
import math
import random
from PIL import Image, ImageDraw
from state_machine import SparkState

# Attempt to load luma.oled and hardware drivers
try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False

class MockOLEDController:
    """Mock OLED Controller that runs when luma.oled or physical hardware is missing."""
    def __init__(self, state_machine):
        self.sm = state_machine
        self.running = False
        self._thread = None
        print("🤖 [MockOLED] Hardware or library missing. Initializing MockOLEDController.")

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._mock_loop, daemon=True)
        self._thread.start()
        print("🤖 [MockOLED] Mock render loop started.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()

    def _mock_loop(self):
        last_state = None
        while self.running:
            current_state = self.sm.get_state()
            if current_state != last_state:
                print(f"🖼️ [MockOLED] State changed to {current_state.name}. Rendering appropriate facial expression to console/logs.")
                last_state = current_state
            time.sleep(0.5)

class OLEDController:
    """Real OLED controller that draws Mimo's cute animated cat face on the SSD1306 display."""
    def __init__(self, state_machine):
        self.sm = state_machine
        self.device = None
        self.running = False
        self._thread = None
        
        if not HAS_HARDWARE:
            self.mock = MockOLEDController(state_machine)
            return

        try:
            # Raspberry Pi 5 I2C Port 1 by default
            serial_interface = i2c(port=1, address=0x3C)
            self.device = ssd1306(serial_interface)
            self.mock = None
            print("📟 [OLED] SSD1306 physical display initialized successfully!")
        except Exception as e:
            print(f"⚠️ [OLED] Failed to initialize physical OLED device: {e}. Falling back to mock mode.")
            self.device = None
            self.mock = MockOLEDController(state_machine)

    def start(self):
        if self.mock:
            self.mock.start()
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()
        print("📟 [OLED] Physical render loop started.")

    def stop(self):
        if self.mock:
            self.mock.stop()
            return
        
        self.running = False
        if self._thread:
            self._thread.join()

    def _render_loop(self):
        frame = 0
        blink_frame = -1
        blink_cooldown = random.randint(100, 200) # ticks at 20 FPS (approx 5-10 seconds)
        
        while self.running:
            try:
                state = self.sm.get_state()
                
                # Check for random blink in IDLE state
                if state == SparkState.IDLE:
                    if blink_frame >= 0:
                        blink_frame += 1
                        if blink_frame > 4: # Blinking lasts 5 frames
                            blink_frame = -1
                            blink_cooldown = random.randint(100, 200)
                    else:
                        blink_cooldown -= 1
                        if blink_cooldown <= 0:
                            blink_frame = 0
                else:
                    blink_frame = -1

                # Render face image
                img = self._draw_face(state, frame, blink_frame)
                
                # Update display
                self.device.display(img)
                
                frame += 1
                time.sleep(0.05) # ~20 FPS
            except Exception as e:
                print(f"⚠️ [OLED Loop Error]: {e}")
                time.sleep(1)

    def _draw_face(self, state, frame, blink_frame) -> Image.Image:
        # Create 1-bit canvas
        img = Image.new("1", (128, 64), 0)
        draw = ImageDraw.Draw(img)
        
        # Center positions for Mimo's eyes
        left_eye_center = (40, 28)
        right_eye_center = (88, 28)
        
        if state == SparkState.LOADING:
            # Animated breathing Zzz bubbles for sleeping/loading state
            draw.text((10, 25), "Mimo Loading...", fill=1)
            # Draw Zzz
            zzz_offset = (frame // 4) % 3
            for i in range(zzz_offset + 1):
                x = 105 + i * 6
                y = 20 - i * 5
                size = 6 + i * 2
                draw.text((x, y), "z", fill=1)
                
        elif state == SparkState.IDLE:
            # Idle state: Wide open cute eyes with blink animation
            if blink_frame == 0 or blink_frame == 4:
                # Half-closed eyes
                draw.ellipse([left_eye_center[0]-10, left_eye_center[1]-5, left_eye_center[0]+10, left_eye_center[1]+5], fill=1)
                draw.ellipse([right_eye_center[0]-10, right_eye_center[1]-5, right_eye_center[0]+10, right_eye_center[1]+5], fill=1)
            elif blink_frame == 1 or blink_frame == 3:
                # Mostly closed eyes (slits)
                draw.line([left_eye_center[0]-12, left_eye_center[1], left_eye_center[0]+12, left_eye_center[1]], fill=1, width=2)
                draw.line([right_eye_center[0]-12, right_eye_center[1], right_eye_center[0]+12, right_eye_center[1]], fill=1, width=2)
            elif blink_frame == 2:
                # Fully closed eyes (horizontal line)
                draw.line([left_eye_center[0]-12, left_eye_center[1]+2, left_eye_center[0]+12, left_eye_center[1]+2], fill=1, width=2)
                draw.line([right_eye_center[0]-12, right_eye_center[1]+2, right_eye_center[0]+12, right_eye_center[1]+2], fill=1, width=2)
            else:
                # Normal wide eyes with light spots/catchlights
                draw.ellipse([left_eye_center[0]-12, left_eye_center[1]-12, left_eye_center[0]+12, left_eye_center[1]+12], fill=1)
                draw.ellipse([right_eye_center[0]-12, right_eye_center[1]-12, right_eye_center[0]+12, right_eye_center[1]+12], fill=1)
                # Catchlight spots (white circles inside black)
                draw.ellipse([left_eye_center[0]-4, left_eye_center[1]-8, left_eye_center[0]+2, left_eye_center[1]-2], fill=0)
                draw.ellipse([right_eye_center[0]-4, right_eye_center[1]-8, right_eye_center[0]+2, right_eye_center[1]-2], fill=0)
                
            # Draw standard cute cat nose and whiskers
            self._draw_whiskers_and_nose(draw)

        elif state == SparkState.LISTENING:
            # Ears twitching, extra large round eyes to represent paying attention
            pulse = int(2 * math.sin(frame * 0.3))
            draw.ellipse([left_eye_center[0]-(13+pulse), left_eye_center[1]-(13+pulse), left_eye_center[0]+(13+pulse), left_eye_center[1]+(13+pulse)], fill=1)
            draw.ellipse([right_eye_center[0]-(13+pulse), right_eye_center[1]-(13+pulse), right_eye_center[0]+(13+pulse), right_eye_center[1]+(13+pulse)], fill=1)
            # Inner sparkles
            draw.ellipse([left_eye_center[0]-3, left_eye_center[1]-7, left_eye_center[0]+3, left_eye_center[1]-1], fill=0)
            draw.ellipse([right_eye_center[0]-3, right_eye_center[1]-7, right_eye_center[0]+3, right_eye_center[1]-1], fill=0)
            
            self._draw_whiskers_and_nose(draw)
            
        elif state == SparkState.THINKING:
            # Dizzy spirals rotating in Mimo's eyes
            angle = (frame * 0.2) % (2 * math.pi)
            for r in [6, 12]:
                # Left eye spiral/dash
                lx = int(left_eye_center[0] + r * math.cos(angle))
                ly = int(left_eye_center[1] + r * math.sin(angle))
                draw.line([left_eye_center[0], left_eye_center[1], lx, ly], fill=1, width=2)
                draw.ellipse([left_eye_center[0]-r, left_eye_center[1]-r, left_eye_center[0]+r, left_eye_center[1]+r], outline=1)
                
                # Right eye spiral/dash
                rx = int(right_eye_center[0] + r * math.cos(angle + math.pi))
                ry = int(right_eye_center[1] + r * math.sin(angle + math.pi))
                draw.line([right_eye_center[0], right_eye_center[1], rx, ry], fill=1, width=2)
                draw.ellipse([right_eye_center[0]-r, right_eye_center[1]-r, right_eye_center[0]+r, right_eye_center[1]+r], outline=1)
                
            self._draw_whiskers_and_nose(draw)

        elif state == SparkState.SPEAKING:
            # Normal wide eyes
            draw.ellipse([left_eye_center[0]-11, left_eye_center[1]-11, left_eye_center[0]+11, left_eye_center[1]+11], fill=1)
            draw.ellipse([right_eye_center[0]-11, right_eye_center[1]-11, right_eye_center[0]+11, right_eye_center[1]+11], fill=1)
            draw.ellipse([left_eye_center[0]-3, left_eye_center[1]-7, left_eye_center[0]+3, left_eye_center[1]-1], fill=0)
            draw.ellipse([right_eye_center[0]-3, right_eye_center[1]-7, right_eye_center[0]+3, right_eye_center[1]-1], fill=0)
            
            # Mouth waveform animation
            mouth_y = 48
            mouth_height = int(5 * math.sin(frame * 0.5)) + 6
            draw.ellipse([64-8, mouth_y - mouth_height//2, 64+8, mouth_y + mouth_height//2], fill=1)
            
            self._draw_whiskers_and_nose(draw, skip_mouth=True)

        elif state == SparkState.ATTENTIVE:
            # Heart Eyes (桃心愛心眼)
            self._draw_heart(draw, left_eye_center[0], left_eye_center[1] - 3, size=11)
            self._draw_heart(draw, right_eye_center[0], right_eye_center[1] - 3, size=11)
            
            # Happy smiling mouth
            draw.arc([64-6, 44, 64, 50], start=0, end=180, fill=1, width=2)
            draw.arc([64, 44, 64+6, 50], start=0, end=180, fill=1, width=2)
            self._draw_whiskers_and_nose(draw, skip_mouth=True)

        elif state == SparkState.ANGRY:
            # Angry slanted eyes
            # Left angry eye (slanted downwards towards center)
            draw.polygon([(left_eye_center[0]-12, left_eye_center[1]-8), 
                          (left_eye_center[0]+12, left_eye_center[1]), 
                          (left_eye_center[0]+8, left_eye_center[1]+10),
                          (left_eye_center[0]-12, left_eye_center[1]+4)], fill=1)
            
            # Right angry eye (slanted downwards towards center)
            draw.polygon([(right_eye_center[0]+12, right_eye_center[1]-8), 
                          (right_eye_center[0]-12, right_eye_center[1]), 
                          (right_eye_center[0]-8, right_eye_center[1]+10),
                          (right_eye_center[0]+12, right_eye_center[1]+4)], fill=1)
            
            # Angry eyebrows
            draw.line([left_eye_center[0]-15, left_eye_center[1]-13, left_eye_center[0]+12, left_eye_center[1]-2], fill=1, width=3)
            draw.line([right_eye_center[0]+15, right_eye_center[1]-13, right_eye_center[0]-12, right_eye_center[1]-2], fill=1, width=3)
            
            # Angry wavy mouth
            draw.line([64-8, 48, 64+8, 48], fill=1, width=2)
            self._draw_whiskers_and_nose(draw, skip_mouth=True)

        return img

    def _draw_whiskers_and_nose(self, draw, skip_mouth=False):
        # Draw tiny nose
        draw.polygon([(64-3, 42), (64+3, 42), (64, 45)], fill=1)
        
        if not skip_mouth:
            # Standard cat w-mouth (curly smile)
            draw.arc([64-6, 42, 64, 48], start=0, end=180, fill=1, width=1)
            draw.arc([64, 42, 64+6, 48], start=0, end=180, fill=1, width=1)
            
        # Left whiskers
        draw.line([25, 43, 8, 41], fill=1, width=1)
        draw.line([25, 46, 5, 47], fill=1, width=1)
        draw.line([25, 49, 9, 54], fill=1, width=1)
        
        # Right whiskers
        draw.line([103, 43, 120, 41], fill=1, width=1)
        draw.line([103, 46, 123, 47], fill=1, width=1)
        draw.line([103, 49, 119, 54], fill=1, width=1)

    def _draw_heart(self, draw, cx, cy, size):
        # Draw heart by drawing two circles and a triangle
        r = size // 2
        # Left lobe
        draw.ellipse([cx - size, cy - size, cx, cy], fill=1)
        # Right lobe
        draw.ellipse([cx, cy - size, cx + size, cy], fill=1)
        # Bottom triangle
        draw.polygon([(cx - size, cy - r), (cx + size, cy - r), (cx, cy + size)], fill=1)
