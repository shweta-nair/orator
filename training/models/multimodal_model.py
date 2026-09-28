"""Assembles the full model graph (spec section 3) from an ExperimentConfig.
Encoders here consume *precomputed* embeddings (see models/speech_encoder.py
and models/visual_encoder.py for how those are produced offline) — this
module only does temporal modeling + fusion + assessment, which is the part
actually trained end-to-end.
"""
import torch.nn as nn
from models.temporal import build_temporal_encoder
from models.fusion import build_fusion
from models.heads import MultiTaskAssessmentHead


class PresentationAssessmentModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.modality = cfg.modality

        if cfg.modality in ("speech", "multimodal"):
            self.speech_temporal = build_temporal_encoder(
                cfg.temporal_model, cfg.speech_embed_dim, cfg.hidden_dim, cfg.num_temporal_layers)
            speech_out_dim = getattr(self.speech_temporal, "out_dim", cfg.hidden_dim)
        else:
            self.speech_temporal = None
            speech_out_dim = 0

        if cfg.modality in ("visual", "multimodal"):
            self.visual_temporal = build_temporal_encoder(
                cfg.temporal_model, cfg.visual_embed_dim, cfg.hidden_dim, cfg.num_temporal_layers)
            visual_out_dim = getattr(self.visual_temporal, "out_dim", cfg.hidden_dim)
        else:
            self.visual_temporal = None
            visual_out_dim = 0

        if cfg.modality == "multimodal":
            self.fusion = build_fusion(cfg.fusion, speech_out_dim, visual_out_dim, cfg.hidden_dim)
            head_in_dim = self.fusion.out_dim
        else:
            self.fusion = None
            head_in_dim = speech_out_dim or visual_out_dim

        self.head = MultiTaskAssessmentHead(head_in_dim, cfg.targets, hidden_dim=cfg.hidden_dim)

    def forward(self, batch):
        speech_repr = self.speech_temporal(batch["speech"], batch.get("speech_mask")) \
            if self.speech_temporal is not None else None
        visual_repr = self.visual_temporal(batch["visual"], batch.get("visual_mask")) \
            if self.visual_temporal is not None else None

        if self.modality == "multimodal":
            fused = self.fusion(speech_repr, visual_repr)
        else:
            fused = speech_repr if speech_repr is not None else visual_repr

        return self.head(fused)


def build_model(cfg):
    return PresentationAssessmentModel(cfg)
