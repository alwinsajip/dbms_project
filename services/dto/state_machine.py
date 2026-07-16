from enum import Enum


class TwinStateMachine(str, Enum):
    IDLE = "idle"
    PROVISIONING = "provisioning"
    APPLYING = "applying"
    REPLAYING = "replaying"
    EVALUATING = "evaluating"
    DESTROYING = "destroying"

    TRANSITIONS = {
        "idle": ["provisioning"],
        "provisioning": ["applying", "destroying"],
        "applying": ["replaying", "destroying"],
        "replaying": ["evaluating", "destroying"],
        "evaluating": ["destroying"],
        "destroying": ["idle"],
    }

    def can_transition_to(self, target: "TwinStateMachine") -> bool:
        return target.value in self.TRANSITIONS.get(self.value, [])
