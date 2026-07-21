import re

PROMPT_INJECTION_PATTERNS = [
    r"ignore.*instructions",
    r"ignore.*system",
    r"forget.*instructions",
    r"reveal.*prompt",
    r"show.*prompt",
    r"developer mode",
    r"jailbreak",
    r"bypass",
    r"api key",
]

DIAGNOSIS_PATTERNS = [
    r"what disease",
    r"do i have",
    r"diagnose",
    r"is this cancer",
    r"is my tooth infected",
]

MEDICATION_PATTERNS = [
    r"prescribe",
    r"medicine",
    r"antibiotic",
    r"painkiller",
    r"ibuprofen",
    r"amoxicillin",
]

EMERGENCY_PATTERNS = [
    r"bleeding",
    r"swelling",
    r"difficulty breathing",
    r"jaw injury",
    r"severe pain",
]

HUMAN_PATTERNS = [
    r"human",
    r"dentist",
    r"staff",
    r"call",
    r"phone",
    r"appointment",
]

def contains_pattern(text, patterns):

    text = text.lower()

    for pattern in patterns:

        if re.search(pattern, text):
            return True

    return False

def safety_check(message: str):

    if contains_pattern(message, PROMPT_INJECTION_PATTERNS):

        return {
            "allowed": False,
            "type": "prompt_injection"
        }

    if contains_pattern(message, DIAGNOSIS_PATTERNS):

        return {
            "allowed": False,
            "type": "diagnosis"
        }

    if contains_pattern(message, MEDICATION_PATTERNS):

        return {
            "allowed": False,
            "type": "medication"
        }

    if contains_pattern(message, EMERGENCY_PATTERNS):

        return {
            "allowed": False,
            "type": "emergency"
        }

    if contains_pattern(message, HUMAN_PATTERNS):

        return {
            "allowed": False,
            "type": "human"
        }

    return {
        "allowed": True,
        "type": "safe"
    }

SAFE_RESPONSES = {

    "prompt_injection":
    "I'm only able to assist with verified Rashid Dental Clinic information and appointment-related questions.",

    "diagnosis":
    "I can't diagnose dental conditions. Please consult a qualified dentist for an examination.",

    "medication":
    "I can't recommend or prescribe medication. Please consult a licensed dental professional.",

    "emergency":
    "Your symptoms may require urgent attention. Please contact Rashid Dental Clinic immediately or visit the nearest emergency department if the situation is severe.",

    "human":
    "Certainly. I can help you connect with the clinic staff or assist you in submitting an appointment request."
}


def get_safe_response(response_type):

    return SAFE_RESPONSES[response_type]