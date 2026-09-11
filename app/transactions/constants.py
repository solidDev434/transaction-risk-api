VALID_TRANSITIONS = {
    "pending": ["flagged", "cleared"],
    "flagged": ["cleared", "rejected"],
    "cleared": [],
    "rejected": []
}
