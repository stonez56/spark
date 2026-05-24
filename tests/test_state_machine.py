import unittest
from state_machine import StateMachine, SparkState

class TestStateMachine(unittest.TestCase):
    def test_initial_state(self):
        """Verify the state machine starts in the IDLE state."""
        sm = StateMachine()
        self.assertEqual(sm.get_state(), SparkState.IDLE)

    def test_transition(self):
        """Verify transitioning to a new state works as expected."""
        sm = StateMachine()
        sm.transition(SparkState.LISTENING)
        self.assertEqual(sm.get_state(), SparkState.LISTENING)

    def test_no_transition_same_state(self):
        """Verify transitioning to the current state is a no-op."""
        sm = StateMachine()
        sm.transition(SparkState.LISTENING)
        self.assertEqual(sm.get_state(), SparkState.LISTENING)
        
        # Transitioning to the same state should keep the state unchanged
        sm.transition(SparkState.LISTENING)
        self.assertEqual(sm.get_state(), SparkState.LISTENING)

    def test_all_states(self):
        """Verify all SparkState enum elements are defined."""
        expected_states = ["IDLE", "LISTENING", "ATTENTIVE", "THINKING", "SPEAKING", "BORED", "YAWN", "ANGRY"]
        for state in expected_states:
            self.assertTrue(hasattr(SparkState, state), f"SparkState is missing state: {state}")

if __name__ == "__main__":
    unittest.main()
