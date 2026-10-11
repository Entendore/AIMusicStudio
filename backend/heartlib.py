"""HeartMuLa Music Generation Backend.
Optimized to support 8GB VRAM GPUs (like GTX 1080) via Lazy Loading and Float16.
"""
import numpy as np
import logging
import os
import tempfile
import subprocess
import time
import soundfile as sf
import torch
from backend.base import MusicBackend

logger = logging.getLogger(__name__)

class Plugin(MusicBackend):
    def __init__(self):
        self.model = "HeartMuLa_CLI"
        self.device = "cpu"
        self.model_path = "E:\\cacheAI"
        self.repo_path = ""

    @classmethod
    def get_metadata(cls):
        return {
            'name': 'HeartMuLa',
            'description': 'Lyrics to song with vocals',
            'details': 'Supports 3B/7B models, GTX 1080 optimization.',
            'icon': '🎤',
            'requirements': 'Requires checkpoints and git repo',
        }

    @classmethod
    def get_prompt_schema(cls):
        return {
            'required': True,
            'title': '📝 Lyrics Input',
            'description': 'Write structured lyrics with section markers like [Intro], [Verse], [Chorus]. '
                           'The music style is controlled by the Tags setting below — not the lyrics text.',
            'placeholder': (
                "[Intro]\n"
                "Soft piano melody playing gently\n"
                "\n"
                "[Verse 1]\n"
                "Walking through the autumn leaves\n"
                "The wind whispers your name\n"
                "\n"
                "[Chorus]\n"
                "I'll find my way back to you\n"
                "No matter how far I roam\n"
                "\n"
                "[Outro]\n"
                "Fading into silence"
            ),
        }

    @classmethod
    def get_settings_schema(cls):
        return [
            # ── Music Style ──────────────────────────
            {'id': 'tags', 'type': 'text', 
             'default': 'piano,happy,wedding,synthesizer,romantic',
             'category': 'Music Style',
             'label': '🎵 Style Tags',
             'description': 'Comma-separated tags that define the sound. '
                            'Example: piano,happy,romantic,synthesizer,rock,electronic',
             'placeholder': 'piano,happy,romantic...'},
            
            # ── Sampling Parameters ──────────────────
            {'id': 'temperature', 'type': 'slider', 'min': 0.1, 'max': 2.0, 
             'default': 1.0, 'step': 0.1,
             'category': 'Sampling',
             'label': '🌡 Temperature',
             'description': 'Controls randomness. Lower = predictable/repetitive, '
                            'Higher = creative/unpredictable. Start with 1.0.'},
            {'id': 'topk', 'type': 'slider', 'min': 1, 'max': 200, 
             'default': 50, 'step': 1,
             'category': 'Sampling',
             'label': '🎯 Top-K',
             'description': 'Limits sampling to the K most likely tokens. '
                            'Lower = more focused, Higher = more diverse.'},
            {'id': 'cfg_scale', 'type': 'slider', 'min': 1.0, 'max': 5.0, 
             'default': 1.5, 'step': 0.1,
             'category': 'Sampling',
             'label': '⚖ CFG Scale',
             'description': 'Classifier-Free Guidance strength. Higher values force '
                            'the model to follow the tags more strictly.'},
            
            # ── Model Selection ──────────────────────
            {'id': 'version', 'type': 'dropdown', 
             'options': ['3B', '7B'], 'default': '3B',
             'category': 'Model',
             'label': '📦 Model Size',
             'description': '3B: Fast, works on 8GB VRAM. 7B: Higher quality, needs 24GB+ VRAM.'},
            
            # ── Performance / VRAM ───────────────────
            {'id': 'lazy_load', 'type': 'dropdown', 
             'options': ['true', 'false'], 'default': 'true',
             'category': 'Performance (VRAM)',
             'label': '⚡ Lazy Load',
             'description': 'Loads model components one at a time to reduce peak VRAM. '
                            'KEEP TRUE for 8GB cards (GTX 1080, RTX 3060).'},
            {'id': 'mula_dtype', 'type': 'dropdown', 
             'options': ['float16', 'bfloat16', 'float32'], 'default': 'float16',
             'category': 'Performance (VRAM)',
             'label': '🔢 Model Precision',
             'description': 'float16 halves VRAM usage with minimal quality loss. '
                            'Use float32 only if you have surplus VRAM.'},
            {'id': 'codec_dtype', 'type': 'dropdown', 
             'options': ['float32', 'float16'], 'default': 'float32',
             'category': 'Performance (VRAM)',
             'label': '🎵 Codec Precision',
             'description': 'Audio encoder/decoder precision. float32 recommended — '
                            'float16 here can cause audio artifacts.'},
        ]

    def load_model(self, config: dict):
        self.device = config['hardware'].get('device', 'cuda')
        self.model_path = config.get('system', {}).get('ckpt_dir', 'E:\\cacheAI')
        self.repo_path = config.get('system', {}).get('heartlib_repo_dir', '')

        if not os.path.exists(self.model_path):
            logger.error(f"HeartMuLa checkpoint directory not found at: {self.model_path}")
            raise FileNotFoundError(f"Checkpoints not found at {self.model_path}")

        self.script_path = os.path.join(self.repo_path, "examples", "run_music_generation.py")
        if not os.path.exists(self.script_path):
            logger.error(f"Could not find official script at: {self.script_path}")
            raise FileNotFoundError(f"Script not found at {self.script_path}")

        # Hardware pre-check for GTX 1080 users
        if self.device == 'cuda':
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"GPU Detected: {torch.cuda.get_device_name(0)} with {total_mem:.1f} GB VRAM.")
            if total_mem <= 9.0:
                logger.warning("⚠️ 8GB VRAM GPU Detected: Ensure 'Lazy Load' is TRUE and 'Model Precision' is FLOAT16!")

        logger.info(f"HeartMuLa CLI script found. Ready to generate via {self.device}.")

    def generate(self, prompt: str, duration: int, params: dict, progress_callback=None, stop_check=None) -> dict:
        tags = params.get('tags', 'pop')
        version = params.get('version', '3B')
        temperature = params.get('temperature', 1.0)
        topk = int(params.get('topk', 50))
        cfg_scale = params.get('cfg_scale', 1.5)
        lazy_load = params.get('lazy_load', 'true') # Default to true for 1080
        mula_dtype = params.get('mula_dtype', 'float16') # Default to float16 for 1080
        codec_dtype = params.get('codec_dtype', 'float32')
        
        max_audio_length_ms = duration * 1000
        
        temp_dir = tempfile.mkdtemp()
        lyrics_path = os.path.join(temp_dir, "lyrics.txt")
        tags_path = os.path.join(temp_dir, "tags.txt")
        output_path = os.path.join(temp_dir, "output.wav")

        with open(lyrics_path, 'w', encoding='utf-8') as f: f.write(prompt)
        with open(tags_path, 'w', encoding='utf-8') as f: f.write(tags)

        # Construct the CLI command with precision and lazy load arguments
        cmd = [
            "python", self.script_path,
            "--model_path", self.model_path,
            "--lyrics", lyrics_path,
            "--tags", tags_path,
            "--save_path", output_path,
            "--max_audio_length_ms", str(max_audio_length_ms),
            "--topk", str(topk),
            "--temperature", str(temperature),
            "--cfg_scale", str(cfg_scale),
            "--version", version,
            "--mula_device", self.device,
            "--codec_device", self.device,
            "--lazy_load", lazy_load,
            "--mula_dtype", mula_dtype,
            "--codec_dtype", codec_dtype
        ]

        logger.info(f"Executing HeartMuLa CLI...")
        if progress_callback: progress_callback(5)

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while process.poll() is None:
                if stop_check and stop_check():
                    process.terminate()
                    logger.warning("HeartMuLa CLI terminated by user.")
                    return None
                time.sleep(0.5)

            if process.returncode != 0:
                stderr_out = process.stderr.read()
                logger.error(f"HeartMuLa CLI Error:\n{stderr_out}")
                return None
                
            if progress_callback: progress_callback(90)

        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return None

        if not os.path.exists(output_path):
            mp3_fallback = output_path.replace('.wav', '.mp3')
            if os.path.exists(mp3_fallback):
                output_path = mp3_fallback
            else:
                logger.error("Generation finished but output file was not created.")
                return None

        try:
            audio_data, sample_rate = sf.read(output_path, dtype='float32')
            if len(audio_data.shape) > 1:
                audio_data = audio_data[:, 0]
            
            if progress_callback: progress_callback(100)
            return {'audio': audio_data, 'sample_rate': sample_rate}
        except Exception as e:
            logger.error(f"Failed to read generated audio: {e}")
            return None

    def unload(self):
        logger.info("HeartMuLa subprocess backend unloaded.")