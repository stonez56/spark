import time
import threading
import os
from PIL import Image, ImageDraw, ImageFont
from state_machine import SparkState

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

try:
    from gpiozero import Servo
    HAS_GPIO = True
except (ImportError, OSError):
    HAS_GPIO = False

class MockGimbalController:
    """Mock controller for SG90 servo gimbal when GPIO or Pi is unavailable."""
    def __init__(self):
        print("🤖 [MockGimbal] Servo gimbal driver missing. Running in MockGimbalController.")
        self.pan_angle = 90
        self.tilt_angle = 90

    def set_angles(self, pan, tilt):
        self.pan_angle = max(0, min(180, pan))
        self.tilt_angle = max(0, min(180, tilt))
        # Log angle updates occasionally or quietly in background
        # print(f"🤖 [MockGimbal] Setting servo angles to Pan: {self.pan_angle}°, Tilt: {self.tilt_angle}°")

class GimbalController:
    """Controls the SG90 servo gimbal using PWM via gpiozero."""
    def __init__(self, pan_pin=18, tilt_pin=19):
        if not HAS_GPIO:
            self.mock = MockGimbalController()
            return
        
        try:
            # gpiozero Servo uses values between -1.0 and 1.0
            # Pin 18 (Pan) and Pin 19 (Tilt)
            self.pan_servo = Servo(pan_pin)
            self.tilt_servo = Servo(tilt_pin)
            self.mock = None
            print(f"🔌 [Gimbal] Servos initialized successfully on GPIO {pan_pin} (Pan) and GPIO {tilt_pin} (Tilt).")
        except Exception as e:
            print(f"⚠️ [Gimbal] Failed to initialize physical GPIO servos: {e}. Falling back to mock.")
            self.mock = MockGimbalController()

    def set_angles(self, pan, tilt):
        if self.mock:
            self.mock.set_angles(pan, tilt)
            return
        
        try:
            # Map 0..180 degrees to -1.0..1.0
            pan_val = (pan / 90.0) - 1.0
            tilt_val = (tilt / 90.0) - 1.0
            self.pan_servo.value = max(-1.0, min(1.0, pan_val))
            self.tilt_servo.value = max(-1.0, min(1.0, tilt_val))
        except Exception as e:
            print(f"⚠️ [Gimbal Error]: {e}")

class CameraController:
    """Handles Pi Camera frames, runs face detection for active wakeup and gimbal tracking."""
    def __init__(self, state_machine, command_queue):
        self.sm = state_machine
        self.command_queue = command_queue
        self.running = False
        self._thread = None
        self.lock = threading.Lock()
        
        self.latest_frame = None
        self.is_mock = not HAS_OPENCV
        self.cap = None
        self.gimbal = GimbalController()
        
        # Current physical target servo angles
        self.pan_angle = 90
        self.tilt_angle = 90

        if not HAS_OPENCV:
            print("🤖 [CameraController] OpenCV not available. Falling back to Mock Camera.")
            return

        # Attempt to open camera (/dev/video0 or /dev/media0 or standard capture index)
        try:
            # Pi Camera IMX219 works through standard OpenCV capture on newer Pi OS
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                # Try capture index 2 or other common ones if 0 fails
                self.cap = cv2.VideoCapture(2)
                
            if not self.cap.isOpened():
                print("⚠️ [CameraController] No physical camera found via cv2.VideoCapture. Falling back to Mock mode.")
                self.is_mock = True
                self.cap = None
            else:
                # Set lower resolution for low-latency background face tracking
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                print("👁️ [CameraController] Physical Pi Camera opened successfully!")
        except Exception as e:
            print(f"⚠️ [CameraController] Error opening camera: {e}. Falling back to Mock mode.")
            self.is_mock = True
            self.cap = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._thread.start()
        print("👁️ [CameraController] Camera thread started.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()
        if self.cap:
            self.cap.release()

    def capture_to_file(self, filepath) -> bool:
        """Saves current frame to a file. Safe, thread-safe, and zero-conflict."""
        with self.lock:
            if self.is_mock or self.latest_frame is None:
                # Generate a beautiful mock camera frame with details
                img = Image.new("RGB", (640, 480), (30, 30, 45))
                draw = ImageDraw.Draw(img)
                # Draw border
                draw.rectangle([(10, 10), (630, 470)], outline=(255, 105, 180), width=3)
                # Draw a cute cat face outline in center
                draw.ellipse([(220, 140), (420, 340)], outline=(255, 255, 255), width=2)
                # Cat ears
                draw.polygon([(220, 180), (200, 80), (280, 150)], outline=(255, 255, 255), width=2)
                draw.polygon([(420, 180), (440, 80), (360, 150)], outline=(255, 255, 255), width=2)
                # Eyes
                draw.ellipse([(270, 210), (300, 240)], fill=(0, 255, 0))
                draw.ellipse([(340, 210), (370, 240)], fill=(0, 255, 0))
                # Nose
                draw.polygon([(315, 260), (325, 260), (320, 266)], fill=(255, 105, 180))
                
                # Metadata text
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                draw.text((30, 30), f"Mimo Vision Cam [SIMULATION]", fill=(255, 255, 255))
                draw.text((30, 420), f"Timestamp: {timestamp}", fill=(200, 200, 200))
                draw.text((30, 440), f"Servos: Pan={self.pan_angle} deg, Tilt={self.tilt_angle} deg", fill=(200, 200, 200))
                
                img.save(filepath, "JPEG")
                print(f"📸 [MockCamera] Generated placeholder frame and saved to {filepath}")
                return True
            else:
                try:
                    # Write the OpenCV frame
                    cv2.imwrite(filepath, self.latest_frame)
                    print(f"📸 [PhysicalCamera] Saved high quality frame to {filepath}")
                    return True
                except Exception as e:
                    print(f"⚠️ [PhysicalCamera] Failed to write frame to file: {e}")
                    return False

    def _camera_loop(self):
        face_cascade = None
        if not self.is_mock:
            try:
                # Load face cascade classifier
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception as e:
                print(f"⚠️ [CameraController] Failed to load Haar Cascade: {e}. Disabling face tracking.")
                face_cascade = None

        # Warm up the camera center gimbal
        self.gimbal.set_angles(self.pan_angle, self.tilt_angle)
        
        last_wakeup_time = 0
        consecutive_face_frames = 0
        
        while self.running:
            start_time = time.time()
            state = self.sm.get_state()
            
            if self.is_mock:
                # Mock background loop behavior - sleep to conserve CPU
                time.sleep(1.5)
                continue

            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue

                # Flip horizontally for natural mirror behavior
                frame = cv2.flip(frame, 1)

                with self.lock:
                    self.latest_frame = frame.copy()

                # Run Face Detection & Gimbal Tracking (Only in IDLE or ATTENTIVE states)
                if face_cascade is not None and state in [SparkState.IDLE, SparkState.ATTENTIVE]:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                    
                    if len(faces) > 0:
                        # Grab the largest face
                        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                        (x, y, w, h) = largest_face
                        face_cx = x + w // 2
                        face_cy = y + h // 2
                        
                        frame_h, frame_w, _ = frame.shape
                        frame_cx = frame_w // 2
                        frame_cy = frame_h // 2
                        
                        # Calculate center offsets
                        offset_x = face_cx - frame_cx
                        offset_y = face_cy - frame_cy
                        
                        # 1. Active Wakeup: Trigger if face is present in IDLE state for multiple frames
                        if state == SparkState.IDLE:
                            consecutive_face_frames += 1
                            if consecutive_face_frames >= 2 and (time.time() - last_wakeup_time > 30):
                                last_wakeup_time = time.time()
                                consecutive_face_frames = 0
                                print("👁️ [PhysicalCamera] User face detected -> triggering active wakeup!")
                                self.command_queue.put({'type': 'wakeup'})
                        
                        # 2. Gimbal Tracking: Adjust Pan/Tilt servo angles based on offset
                        # Simple proportional steering
                        pan_step = 0
                        tilt_step = 0
                        
                        if abs(offset_x) > 15:
                            # If face is to the right (positive offset), turn camera right (increase pan)
                            pan_step = 1 if offset_x > 0 else -1
                        if abs(offset_y) > 15:
                            # If face is lower (positive offset), tilt down (increase tilt)
                            tilt_step = 1 if offset_y > 0 else -1
                            
                        if pan_step != 0 or tilt_step != 0:
                            self.pan_angle = max(20, min(160, self.pan_angle + pan_step))
                            self.tilt_angle = max(30, min(150, self.tilt_angle + tilt_step))
                            self.gimbal.set_angles(self.pan_angle, self.tilt_angle)
                    else:
                        consecutive_face_frames = max(0, consecutive_face_frames - 1)
                        
                # Limit loop speed to ~15 FPS to conserve CPU on Pi 5
                elapsed = time.time() - start_time
                sleep_time = max(0.005, 0.066 - elapsed)
                time.sleep(sleep_time)

            except Exception as e:
                print(f"⚠️ [CameraController Loop Error]: {e}")
                time.sleep(1)
