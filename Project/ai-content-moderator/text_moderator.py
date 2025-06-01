from langdetect import detect, DetectorFactory
from transformers import pipeline, MarianMTModel, MarianTokenizer
import re
import os

DetectorFactory.seed = 0

# --- Model Loading (Global to avoid reloading on every request) ---
try:
    toxicity_classifier = pipeline("text-classification", model="s-nlp/roberta_toxicity_classifier", truncation=True)
except Exception as e:
    print(f"Error loading toxicity classifier: {e}. Please check your internet connection or model availability.")
    toxicity_classifier = None

translation_model_name = "Helsinki-NLP/opus-mt-hi-en"
translator_tokenizer = None
translator_model = None

try:
    translator_tokenizer = MarianTokenizer.from_pretrained(translation_model_name)
    translator_model = MarianMTModel.from_pretrained(translation_model_name)
except Exception as e:
    print(f"Error loading translation model: {e}. Please check your internet connection or model availability.")

hinglish_keywords = ['kutte', 'chutiya', 'bhosdi', 'madarchod', 'kamina', 'harami', 'gandu', 'behenchod', 'lund', 'saala']

def is_hinglish(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in hinglish_keywords)

def translate_to_english(text):
    if translator_tokenizer is None or translator_model is None:
        return "Translation service unavailable."

    try:
        tokens = translator_tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        translation = translator_model.generate(**tokens)
        return translator_tokenizer.decode(translation[0], skip_special_tokens=True)
    except Exception as e:
        print(f"Error during translation: {e}")
        return text

def check_text_content(text):
    original_text = text
    processed_text = text
    language = "unknown"
    
    result = {
        "language": language,
        "original_text": original_text,
        "processed_text": processed_text,
        "label": "UNKNOWN",
        "score": 0.0,
        "safe": True,
        "error": None
    }

    try:
        language = detect(text)
        result["language"] = language
    except Exception as e:
        result["error"] = f"Language detection failed: {str(e)}"

    if language == 'hi' or (language == 'en' and is_hinglish(text)):
        translated_text = translate_to_english(text)
        if translated_text == "Translation service unavailable.":
            result["error"] = (result["error"] + "; " if result["error"] else "") + "Translation service failed to load."
            processed_text = original_text
        else:
            processed_text = translated_text
        result["processed_text"] = processed_text

    if toxicity_classifier is None:
        result["error"] = (result["error"] + "; " if result["error"] else "") + "Toxicity classifier failed to load."
        result["safe"] = True
        result["label"] = "CLASSIFIER_UNAVAILABLE"
        return result

    try:
        classifier_output = toxicity_classifier(processed_text)[0]
        result["label"] = classifier_output['label']
        result["score"] = round(classifier_output['score'], 4)
        
        # --- ADJUSTED TOXICITY LOGIC WITH THRESHOLD ---
        # Define a confidence threshold for flagging as toxic
        TOXICITY_SCORE_THRESHOLD = 0.75 # If the 'toxic' label's score is above this, it's toxic
                                        # You can adjust this value (e.g., 0.6, 0.8, 0.9)

        # The 's-nlp/roberta_toxicity_classifier' model outputs 'not_toxic' or 'toxic'
        # We only flag as toxic if the label is 'toxic' AND the score for 'toxic' is high enough
        if result["label"].lower() == "toxic" and result["score"] >= TOXICITY_SCORE_THRESHOLD:
            result["safe"] = False
        else:
            result["safe"] = True
        # --- END ADJUSTED TOXICITY LOGIC ---

        # --- DEBUGGING: Print raw classifier output ---
        print(f"Text Classifier Raw Output for '{processed_text}': {classifier_output}")
        # --- END DEBUGGING ---

    except Exception as e:
        result["error"] = (result["error"] + "; " if result["error"] else "") + f"Toxicity classification failed: {str(e)}"
        result["safe"] = True
        result["label"] = "CLASSIFICATION_ERROR"

    return result