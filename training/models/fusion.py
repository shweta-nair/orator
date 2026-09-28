"""Multimodal fusion (spec section 11, Experiment 8)."""
import torch
import torch.nn as nn


class ConcatFusion(nn.Module):
    """Baseline: [speech_embedding ; visual_embedding] -> linear projection."""
    def __init__(self, speech_dim, visual_dim, out_dim):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(speech_dim + visual_dim, out_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
        )
        self.out_dim = out_dim

    def forward(self, speech_repr, visual_repr):
        return self.proj(torch.cat([speech_repr, visual_repr], dim=-1))


class CrossAttentionFusion(nn.Module):
    """Advanced fusion: speech attends over visual and vice versa, then combined."""
    def __init__(self, speech_dim, visual_dim, out_dim, num_heads=4):
        super().__init__()
        d = out_dim
        self.speech_in = nn.Linear(speech_dim, d)
        self.visual_in = nn.Linear(visual_dim, d)
        self.speech_to_visual = nn.MultiheadAttention(d, num_heads, batch_first=True)
        self.visual_to_speech = nn.MultiheadAttention(d, num_heads, batch_first=True)
        self.out_proj = nn.Sequential(nn.Linear(d * 2, out_dim), nn.ReLU(), nn.Dropout(0.2))
        self.out_dim = out_dim

    def forward(self, speech_repr, visual_repr):
        # treat each pooled modality vector as a length-1 sequence for cross-attention
        s = self.speech_in(speech_repr).unsqueeze(1)
        v = self.visual_in(visual_repr).unsqueeze(1)
        s_attn, _ = self.speech_to_visual(s, v, v)
        v_attn, _ = self.visual_to_speech(v, s, s)
        combined = torch.cat([s_attn.squeeze(1), v_attn.squeeze(1)], dim=-1)
        return self.out_proj(combined)


def build_fusion(kind: str, speech_dim: int, visual_dim: int, out_dim: int):
    if kind == "concat":
        return ConcatFusion(speech_dim, visual_dim, out_dim)
    if kind == "attention":
        return CrossAttentionFusion(speech_dim, visual_dim, out_dim)
    raise ValueError(f"unknown fusion kind: {kind}")
