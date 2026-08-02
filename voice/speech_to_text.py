class SpeechToText:
    """AIOS speech recognition foundation."""

    def transcribe(self, audio):
        return {
            "audio": audio,
            "text": ""
        }
