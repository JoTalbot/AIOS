class OCRProcessor:
    """OCR processing adapter foundation."""

    def analyze(self, image):
        return {
            "image": image,
            "text": []
        }
