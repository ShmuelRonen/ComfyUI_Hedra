"""
ComfyUI-Hedra
A ComfyUI custom node for Hedra Character-3 API integration
Converts images to talking avatar videos using audio input
"""

from .hedra_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

# Required for ComfyUI to recognize the nodes
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

# Web directory for custom widgets (if any)
WEB_DIRECTORY = "./web"

# Optional: Add any initialization code here
def init():
    pass

# Optional: Add any cleanup code here
def cleanup():
    pass

# Optional: Version check or dependencies check
try:
    import cv2
    import scipy
    import numpy as np
    import requests
    import torch
except ImportError as e:
    print(f"[ComfyUI-Hedra] Missing required dependency: {e}")
    print("[ComfyUI-Hedra] Please install requirements: pip install opencv-python scipy numpy requests torch")