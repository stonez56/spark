import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from state_machine import SparkState

# Audio settings for openWakeWord
FORMAT = np.int16
CHANNELS = 1
RATE = 16000
CHUNK = 1280 # 80 ms chunks

def listen_for_wake_word(state_machine, state_queue, audio_queue, wake_word="alexa"):
    """
    Listens continuously on the audio_queue (from browser WebSocket) and transitions the state machine
    when the wake word is detected.
    """
    print(f"\nLoading openWakeWord model for '{wake_word}'...")
    try:
        import openwakeword
        paths = [p for p in openwakeword.get_pretrained_model_paths() if wake_word in p]
        if not paths:
            print(f"Could not find model for '{wake_word}'. Loading all default models.")
            oww_model = Model()
        else:
            oww_model = Model(wakeword_model_paths=paths)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Please check openWakeWord installation and models.")
        return

    print("Waiting for audio stream from browser...")
    
    try:
        while True:
            # Get binary audio chunk from the queue (blocking)
            if not audio_queue.empty():
                audio_bytes = audio_queue.get()
                
                # Convert bytes to numpy int16 array
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                
                # Feed to model
                prediction = oww_model.predict(audio_data)
                
                # Check if any wake word was triggered above threshold
                for mdl_name, score in prediction.items():
                    if score > 0.5: # Threshold can be tuned
                        print(f"Wake word detected! ({mdl_name}: {score:.2f})")
                        
                        # If we are IDLE, transition to LISTENING
                        if state_machine.get_state() == SparkState.IDLE:
                            state_machine.transition(SparkState.LISTENING)
                            state_queue.put(SparkState.LISTENING)
                            
                        # Reset model to avoid continuous triggering
                        oww_model.reset()
            else:
                # Sleep briefly to avoid pegging CPU if queue is empty
                import time
                time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\nStopping wake word listener.")
    except Exception as e:
        print(f"Error processing audio stream: {e}")

if __name__ == "__main__":
    # Simple test without full state machine
    from multiprocessing import Queue
    class MockStateMachine:
        def __init__(self):
            self.state = SparkState.IDLE
        def get_state(self): return self.state
        def transition(self, state): 
            self.state = state
            print(f"Mock State transitioned to {state.name}")
            
    test_state_queue = Queue()
    test_audio_queue = Queue()
    test_sm = MockStateMachine()
    listen_for_wake_word(test_sm, test_state_queue, test_audio_queue)
