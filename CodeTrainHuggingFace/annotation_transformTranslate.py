import os
import json
import langdetect

from tqdm import tqdm
from glob import glob

FAIRSEQ_LANGUAGE_CODES = ['ace_Arab', 'ace_Latn', 'acm_Arab', 'acq_Arab', 'aeb_Arab', 'afr_Latn', 'ajp_Arab', 'aka_Latn', 'amh_Ethi', 'apc_Arab', 'arb_Arab', 'ars_Arab', 'ary_Arab', 'arz_Arab', 'asm_Beng', 'ast_Latn', 'awa_Deva', 'ayr_Latn', 'azb_Arab', 'azj_Latn', 'bak_Cyrl', 'bam_Latn', 'ban_Latn', 'bel_Cyrl', 'bem_Latn', 'ben_Beng', 'bho_Deva', 'bjn_Arab', 'bjn_Latn', 'bod_Tibt', 'bos_Latn', 'bug_Latn', 'bul_Cyrl', 'cat_Latn', 'ceb_Latn', 'ces_Latn', 'cjk_Latn', 'ckb_Arab', 'crh_Latn', 'cym_Latn', 'dan_Latn', 'deu_Latn', 'dik_Latn', 'dyu_Latn', 'dzo_Tibt', 'ell_Grek', 'eng_Latn', 'epo_Latn', 'est_Latn', 'eus_Latn', 'ewe_Latn', 'fao_Latn', 'pes_Arab', 'fij_Latn', 'fin_Latn', 'fon_Latn', 'fra_Latn', 'fur_Latn', 'fuv_Latn', 'gla_Latn', 'gle_Latn', 'glg_Latn', 'grn_Latn', 'guj_Gujr', 'hat_Latn', 'hau_Latn', 'heb_Hebr', 'hin_Deva', 'hne_Deva', 'hrv_Latn', 'hun_Latn', 'hye_Armn', 'ibo_Latn', 'ilo_Latn', 'ind_Latn', 'isl_Latn', 'ita_Latn', 'jav_Latn', 'jpn_Jpan', 'kab_Latn', 'kac_Latn', 'kam_Latn', 'kan_Knda', 'kas_Arab', 'kas_Deva', 'kat_Geor', 'knc_Arab', 'knc_Latn', 'kaz_Cyrl', 'kbp_Latn', 'kea_Latn', 'khm_Khmr', 'kik_Latn', 'kin_Latn', 'kir_Cyrl', 'kmb_Latn', 'kon_Latn', 'kor_Hang', 'kmr_Latn', 'lao_Laoo', 'lvs_Latn', 'lij_Latn', 'lim_Latn', 'lin_Latn', 'lit_Latn', 'lmo_Latn', 'ltg_Latn', 'ltz_Latn', 'lua_Latn', 'lug_Latn', 'luo_Latn', 'lus_Latn', 'mag_Deva', 'mai_Deva', 'mal_Mlym', 'mar_Deva', 'min_Latn', 'mkd_Cyrl', 'plt_Latn', 'mlt_Latn', 'mni_Beng', 'khk_Cyrl', 'mos_Latn', 'mri_Latn', 'zsm_Latn', 'mya_Mymr', 'nld_Latn', 'nno_Latn', 'nob_Latn', 'npi_Deva', 'nso_Latn', 'nus_Latn', 'nya_Latn', 'oci_Latn', 'gaz_Latn', 'ory_Orya', 'pag_Latn', 'pan_Guru', 'pap_Latn', 'pol_Latn', 'por_Latn', 'prs_Arab', 'pbt_Arab', 'quy_Latn', 'ron_Latn', 'run_Latn', 'rus_Cyrl', 'sag_Latn', 'san_Deva', 'sat_Beng', 'scn_Latn', 'shn_Mymr', 'sin_Sinh', 'slk_Latn', 'slv_Latn', 'smo_Latn', 'sna_Latn', 'snd_Arab', 'som_Latn', 'sot_Latn', 'spa_Latn', 'als_Latn', 'srd_Latn', 'srp_Cyrl', 'ssw_Latn', 'sun_Latn', 'swe_Latn', 'swh_Latn', 'szl_Latn', 'tam_Taml', 'tat_Cyrl', 'tel_Telu', 'tgk_Cyrl', 'tgl_Latn', 'tha_Thai', 'tir_Ethi', 'taq_Latn', 'taq_Tfng', 'tpi_Latn', 'tsn_Latn', 'tso_Latn', 'tuk_Latn', 'tum_Latn', 'tur_Latn', 'twi_Latn', 'tzm_Tfng', 'uig_Arab', 'ukr_Cyrl', 'umb_Latn', 'urd_Arab', 'uzn_Latn', 'vec_Latn', 'vie_Latn', 'war_Latn', 'wol_Latn', 'xho_Latn', 'ydd_Hebr', 'yor_Latn', 'yue_Hant', 'zho_Hans', 'zho_Hant', 'zul_Latn']

lang_map = {
    "af": "afr_Latn",     # Afrikaans
    "am": "amh_Ethi",     # Amharic
    "ar": "arb_Arab",     # Arabic
    "az": "azj_Latn",     # Azerbaijani
    "be": "bel_Cyrl",     # Belarusian
    "bg": "bul_Cyrl",     # Bulgarian
    "bn": "ben_Beng",     # Bengali
    "bs": "bos_Latn",     # Bosnian
    "ca": "cat_Latn",     # Catalan
    "ceb": "ceb_Latn",    # Cebuano
    "cs": "ces_Latn",     # Czech
    "cy": "cym_Latn",     # Welsh
    "da": "dan_Latn",     # Danish
    "de": "deu_Latn",     # German
    "el": "ell_Grek",     # Greek
    "en": "eng_Latn",     # English
    "es": "spa_Latn",     # Spanish
    "et": "est_Latn",     # Estonian
    "eu": "eus_Latn",     # Basque
    "fa": "pes_Arab",     # Persian
    "fi": "fin_Latn",     # Finnish
    "fil": "fil_Latn",    # Filipino
    "fr": "fra_Latn",     # French
    "ga": "gle_Latn",     # Irish
    "gl": "glg_Latn",     # Galician
    "gu": "guj_Gujr",     # Gujarati
    "he": "heb_Hebr",     # Hebrew
    "hi": "hin_Deva",     # Hindi
    "hr": "hrv_Latn",     # Croatian
    "ht": "hat_Latn",     # Haitian Creole
    "hu": "hun_Latn",     # Hungarian
    "hy": "hye_Armn",     # Armenian
    "id": "ind_Latn",     # Indonesian
    "is": "isl_Latn",     # Icelandic
    "it": "ita_Latn",     # Italian
    "ja": "jpn_Jpan",     # Japanese
    "jv": "jav_Latn",     # Javanese
    "ka": "kat_Geor",     # Georgian
    "kk": "kaz_Cyrl",     # Kazakh
    "km": "khm_Khmr",     # Khmer
    "kn": "kan_Knda",     # Kannada
    "ko": "kor_Hang",     # Korean
    "la": "lat_Latn",     # Latin
    "lo": "lao_Laoo",     # Lao
    "lt": "lit_Latn",     # Lithuanian
    "lv": "lvs_Latn",     # Latvian
    "mk": "mkd_Cyrl",     # Macedonian
    "ml": "mal_Mlym",     # Malayalam
    "mn": "khk_Cyrl",     # Mongolian
    "mr": "mar_Deva",     # Marathi
    "ms": "zsm_Latn",     # Malay
    "my": "mya_Mymr",     # Burmese
    "ne": "npi_Deva",     # Nepali
    "nl": "nld_Latn",     # Dutch
    "no": "nob_Latn",     # Norwegian
    "pa": "pan_Guru",     # Punjabi
    "pl": "pol_Latn",     # Polish
    "pt": "por_Latn",     # Portuguese
    "ro": "ron_Latn",     # Romanian
    "ru": "rus_Cyrl",     # Russian
    "si": "sin_Sinh",     # Sinhala
    "sk": "slk_Latn",     # Slovak
    "sl": "slv_Latn",     # Slovenian
    "so": "som_Latn",     # Somali
    "sq": "als_Latn",     # Albanian
    "sr": "srp_Cyrl",     # Serbian
    "su": "sun_Latn",     # Sundanese
    "sv": "swe_Latn",     # Swedish
    "sw": "swh_Latn",     # Swahili
    "ta": "tam_Taml",     # Tamil
    "te": "tel_Telu",     # Telugu
    "th": "tha_Thai",     # Thai
    "tl": "tgl_Latn",     # Tagalog
    "tr": "tur_Latn",     # Turkish
    "uk": "ukr_Cyrl",     # Ukrainian
    "ur": "urd_Arab",     # Urdu
    "uz": "uzn_Latn",     # Uzbek
    "vi": "vie_Latn",     # Vietnamese
    "zh-cn": "zho_Hans",  # Chinese Simplified
    "zh-tw": "zho_Hant",  # Chinese Traditional
    "zh": "zho_Hans",     # Default to simplified
}

print(os.getcwd())
DATA_FOLDER = os.path.join('data')
TRAIN_FOLDER = os.path.join(DATA_FOLDER, 'train')

JSON_FILES = glob(os.path.join(TRAIN_FOLDER, "JSON/*.json"))
print(f"Found JSON: {len(JSON_FILES)} files")

def detect_lang(text):
    try:
        iso = langdetect.detect(text)

        return lang_map.get(iso, "eng_Latn")    
    except:
        return "eng_Latn"
    
def convertJson2Tsv():
    with open(os.path.join("translate", "train.tsv"), "w", encoding="utf-8") as outFile:
        for filePath in tqdm(JSON_FILES, desc="Processing"):
            with open(filePath, "r", encoding="utf-8") as currentFile:
                try:
                    jsonData = json.load(currentFile)

                    cells = jsonData.get("cells", [])

                    for cell in cells:
                        src = cell.get("text", "").strip()
                        tgt = cell.get("text_vi", "").strip()

                        src_lang = detect_lang(src)

                        if len(src) <= 15 or len(tgt) <= 15:
                            continue

                        if src and tgt:
                            src = src.replace('"', "")
                            tgt = tgt.replace('"', "")

                            src = src.replace("\t", " ")
                            tgt = tgt.replace("\t", " ")

                            line = f"{src_lang}\t{src}\t{tgt}\n"
                            cleaned_line = line.replace('\x00', '')
                            outFile.write(cleaned_line)

                except Exception as e:
                    print(f"Get error with reading file: {e}")
def preprocessData():
    pass
convertJson2Tsv()