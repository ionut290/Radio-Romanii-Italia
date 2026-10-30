#!/usr/bin/env python3
"""AST GTZAN fbank preprocessing, NumPy-only and free of PyTorch dependencies.

Implements the known NumPy branch of HuggingFace ASTFeatureExtractor 4.48.3,
including windowing, Kaldi mel bank, padding, preemphasis and normalization.
Requires the model's pinned preprocessor_config.json and local transformers.
"""
import json
from pathlib import Path

def ast_features(audio, config_path):
    import numpy as np
    from transformers.audio_utils import mel_filter_bank, spectrogram, window_function

    cfg=json.loads(Path(config_path).read_text(encoding="utf-8"))
    if (cfg.get("feature_extractor_type"), cfg.get("sampling_rate"),
        cfg.get("max_length"),cfg.get("num_mel_bins")) != (
        "ASTFeatureExtractor",16000,1024,128):
        raise ValueError("Incompatible AST GTZAN preprocessing configuration")

    wave=np.asarray(audio,dtype=np.float32).reshape(-1)
    if len(wave)<16000 or not np.isfinite(wave).all():
        raise ValueError("Invalid audio for AST classifier")
    banks=mel_filter_bank(
        num_frequency_bins=256,num_mel_filters=128,
        min_frequency=20,max_frequency=8000,sampling_rate=16000,
        norm=None,mel_scale="kaldi",triangularize_in_mel_space=True)
    banks=np.pad(banks,((0,1),(0,0)))
    window=window_function(400,"hann",periodic=False)
    fb=spectrogram(
        wave,window,
        frame_length=400,hop_length=160,fft_length=512,power=2.0,
        center=False,preemphasis=0.97,mel_filters=banks,
        log_mel="log",mel_floor=1.192092955078125e-07,
        remove_dc_offset=True).T
    # 4.48.3 ASTFeatureExtractor pads with zero fbank frames BEFORE normalizing.
    frames=1024
    if fb.shape[0]<frames:
        fb=np.pad(fb,((0,frames-fb.shape[0]),(0,0)))
    else:
        fb=fb[:frames,:]
    if bool(cfg.get("do_normalize",True)):
        mean=float(cfg.get("mean",-4.2677393))
        std=float(cfg.get("std",4.5689974))
        fb=(fb-mean)/(std*2)
    result=np.asarray(fb,dtype=np.float32).reshape(1,1024,128)
    if not np.isfinite(result).all():
        raise ValueError("Non-finite AST features")
    return result
