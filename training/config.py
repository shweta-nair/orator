"""Experiment configuration. One dict per experiment named in spec section 21."""
from dataclasses import dataclass, field


@dataclass
class ExperimentConfig:
    name: str
    manifest_path: str = "data/manifest.csv"
    modality: str = "multimodal"       # speech | visual | multimodal
    temporal_model: str = "lstm"        # none | lstm | gru | transformer
    fusion: str = "concat"              # concat | attention
    speech_embed_dim: int = 768         # matches common wav2vec2/HuBERT hidden size
    visual_embed_dim: int = 512         # matches a resnet18/ViT-small pooled output
    hidden_dim: int = 256
    num_temporal_layers: int = 2
    targets: tuple = ("fluency", "eye_contact", "overall_delivery")
    batch_size: int = 8
    lr: float = 1e-4
    epochs: int = 30
    patience: int = 5                    # early stopping
    seed: int = 42
    checkpoint_dir: str = "checkpoints"
    device: str = "cpu"


EXPERIMENTS = {
    "speech_only": ExperimentConfig(name="speech_only", modality="speech", temporal_model="none"),
    "visual_only": ExperimentConfig(name="visual_only", modality="visual", temporal_model="none"),
    "multimodal_no_temporal": ExperimentConfig(name="multimodal_no_temporal", modality="multimodal", temporal_model="none"),
    "multimodal_lstm": ExperimentConfig(name="multimodal_lstm", modality="multimodal", temporal_model="lstm"),
    "multimodal_gru": ExperimentConfig(name="multimodal_gru", modality="multimodal", temporal_model="gru"),
    "multimodal_transformer": ExperimentConfig(name="multimodal_transformer", modality="multimodal", temporal_model="transformer"),
    "multimodal_attention_fusion": ExperimentConfig(name="multimodal_attention_fusion", modality="multimodal", temporal_model="lstm", fusion="attention"),
}
