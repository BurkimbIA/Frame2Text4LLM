from .easyocr import EasyOCR
from .mistralocr import MistralOCR
from .openaiocr import OpenAIOCR
from .paddleocr import PaddleOCR
from .vlmocr import VLMOCR

OCR_TOOLS = {
    "paddleocr": PaddleOCR,
    "openai": OpenAIOCR,
    "mistral": MistralOCR,
    "easyocr": EasyOCR,
    "vlm": VLMOCR,
}
