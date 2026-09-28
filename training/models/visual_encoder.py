"""Offline visual feature extraction — samples frames from a video and runs
them through a pretrained CNN backbone to produce the .npy embeddings the
training pipeline consumes. Separate from the training loop for the same
reason as speech_encoder.py: swap the backbone here without touching
model/training code.

Requires: torch, torchvision, opencv-python (opencv-python-headless already
in requirements.txt for the Flask app; torch/torchvision are training-only).
"""
import numpy as np
import cv2


def sample_frames(video_path: str, fps_target: float = 2.0):
    cap = cv2.VideoCapture(video_path)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, round(src_fps / fps_target))
    frames = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        i += 1
    cap.release()
    return frames


def extract_features(video_path: str, backbone: str = "resnet18", fps_target: float = 2.0) -> np.ndarray:
    """Returns a [T, 512] array of per-sampled-frame pooled CNN features
    (resnet18 pooled output). Swap backbone for a ViT/EfficientNet/MobileNet
    to compare visual encoders (spec section 7/9)."""
    import torch
    import torchvision
    from torchvision import transforms

    weights = torchvision.models.ResNet18_Weights.DEFAULT
    model = torchvision.models.resnet18(weights=weights)
    model.fc = torch.nn.Identity()  # use the 512-d pooled feature, not the classifier
    model.eval()

    preprocess = transforms.Compose([
        transforms.ToTensor(),
        transforms.Resize((224, 224)),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    frames = sample_frames(video_path, fps_target)
    if not frames:
        return np.zeros((0, 512), dtype=np.float32)

    batch = torch.stack([preprocess(f) for f in frames])
    with torch.no_grad():
        feats = model(batch)
    return feats.numpy()  # [T, 512]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python visual_encoder.py <video.mp4> <out.npy>")
        raise SystemExit(1)
    feats = extract_features(sys.argv[1])
    np.save(sys.argv[2], feats)
    print("saved", feats.shape, "to", sys.argv[2])
