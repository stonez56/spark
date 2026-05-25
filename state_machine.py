import enum

class SparkState(enum.Enum):
    LOADING = "Loading"
    IDLE = "Idle"
    LISTENING = "Listening"
    ATTENTIVE = "Attentive"
    THINKING = "Thinking"
    SPEAKING = "Speaking"
    BORED = "Bored"
    YAWN = "Yawn"
    ANGRY = "Angry"

class StateMachine:
    def __init__(self):
        self.current_state = SparkState.LOADING

    def transition(self, new_state: SparkState):
        if self.current_state != new_state:
            print(f"State transitioned from {self.current_state.name} to {new_state.name}")
            self.current_state = new_state
            
    def get_state(self):
        return self.current_state
