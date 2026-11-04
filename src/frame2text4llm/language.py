"""Which language a window is spoken in, and which one its subtitle is written in. From gom-dɛɛsa
(BurkimbIA/bia-speech-translation): a video subtitled in French may be spoken in French, or mix a French
narrator with speakers of Moore, and only the windows spoken in the other language are a translation pair."""

import re
import string

try:  # the lid extra: written_in needs none of it
    import soundfile as sf
    import torch
    from transformers import AutoFeatureExtractor, Wav2Vec2ForSequenceClassification
except ImportError:
    torch = None

# function words of one language and not the other
FRENCH = set(
    "le les de des du je tu il elle est et que qui pas vous nous un une ce cette ces mais pour avec dans sur "
    "mon mes ton tes ses au aux suis es ai as avons sont ont fait ça comme bien oui non très tout rien moi "
    "toi lui leur quoi où quand comment pourquoi".split()
)
ENGLISH = set(
    "the and you is are i what to of it that this we they he she my your be was were have has do does not "
    "yes for with at will can don't i'm it's".split()
)


def written_in(text: str) -> str:
    """ "french", "english" or "other" (another language, names, a title), by counting function words; "other"
    when they tie."""
    words = [w.lower().strip(string.punctuation + "«»…") for w in re.split(r"[\s']+", text)]
    f, e = sum(w in FRENCH for w in words), sum(w in ENGLISH for w in words)
    return "french" if f > e else "english" if e > f else "other"


class LanguageID:
    """MMS-LID (facebook/mms-lid-256, 256 languages) on audio files of 16 kHz mono, such as the windows
    AudioGenerator cuts. `languages` maps the ISO 639-3 codes whose probabilities are kept to column names."""

    def __init__(
        self,
        model_name: str = "facebook/mms-lid-256",
        languages: dict[str, str] | None = None,
        device: str | None = None,
    ):
        if torch is None:
            raise ImportError("LanguageID needs the lid extra: pip install 'frame2text4llm[lid]'")
        from .ocr.tools.vlmocr import pick_device

        self.languages = languages or {"mos": "moore", "dyu": "dioula", "bam": "bambara", "fra": "french"}
        self.device = device or pick_device()
        half = self.device != "cpu"
        self.extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.model = Wav2Vec2ForSequenceClassification.from_pretrained(
            model_name, dtype=torch.float16 if half else torch.float32
        )
        self.model = self.model.to(self.device).eval()
        self.dtype = torch.float16 if half else torch.float32
        self.label = {code: i for i, code in self.model.config.id2label.items()}  # its label2id is empty

    def hear(self, paths: list[str], batch: int = 8) -> list[dict[str, float | str]]:
        """For each file, the language heard most (by `languages`' name when it is one of them, else its
        code) and the probability of each of `languages`. Files are sorted by length, so that a batch pads
        little."""
        waves = [sf.read(path, dtype="float32")[0] for path in paths]
        heard: list[dict] = [{} for _ in waves]
        order = sorted(range(len(waves)), key=lambda i: len(waves[i]))
        for b in range(0, len(order), batch):
            chunk = order[b : b + batch]
            x = self.extractor(
                [waves[i] for i in chunk], sampling_rate=16000, padding=True, return_tensors="pt"
            )
            mask = x.get("attention_mask")
            with torch.no_grad():
                logits = self.model(
                    x.input_values.to(self.device, self.dtype),
                    attention_mask=None if mask is None else mask.to(self.device),
                ).logits
            for i, prob in zip(chunk, logits.float().softmax(-1).cpu(), strict=True):
                top = self.model.config.id2label[int(prob.argmax())]
                heard[i] = {
                    "language": self.languages.get(top, top),
                    **{
                        name: round(float(prob[self.label[code]]), 3) for code, name in self.languages.items()
                    },
                }
        return heard
