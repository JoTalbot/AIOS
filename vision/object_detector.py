class ObjectDetector:
    """AIOS object detection foundation."""

    def detect(self, image):
        return {
            "image": image,
            "objects": []
        }
