import queue,sys,threading,time,sounddevice as sd,speech_recognition as sr,numpy as np,tempfile,wave,os,json,re,platform
import tkinter as tk
from tkinter import scrolledtext,ttk,filedialog
from deep_translator import GoogleTranslator
try:from deep_translator import MyMemoryTranslator,LingueeTranslator
except ImportError:print("Some translation engines are not available in your deep_translator version")
import concurrent.futures
from functools import lru_cache
try:
    from pypinyin import pinyin,Style
    PINYIN_AVAILABLE =True
    print("pypinyin support is available, Chinese pronunciation will be available")
except ImportError:
    PINYIN_AVAILABLE =False
    print("pypinyin not installed. Chinese pronunciation will be limited.")
try:
    import transliterate
    TRANSLITERATE_AVAILABLE =True
    print("transliterate support is available, most language pronunciations will be available")
except ImportError:
    TRANSLITERATE_AVAILABLE =False
    print("transliterate not installed. Some language pronunciations will be limited.")
try:
    import indic_transliteration
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import SchemeMap,SCHEMES,transliterate
    INDIC_AVAILABLE =True
    print("Indic transliteration support is available, Hindi/Sanskrit pronunciation will be available")
except ImportError:
    INDIC_AVAILABLE =False
    print("indic_transliteration not installed. Hindi/Sanskrit pronunciation will be limited.")
try:
    import pykakasi
    JAPANESE_AVAILABLE =True
    print("pykakasi support is available, Japanese romanization will be available")
except ImportError:
    JAPANESE_AVAILABLE =False
    print("pykakasi not installed. Japanese pronunciation will be limited.")
try:
    import pyttsx3
    TTS_AVAILABLE =True
    print("Text-to-speech is available")
    tts_engine =pyttsx3.init()
except ImportError:
    TTS_AVAILABLE =False
    print("pyttsx3 not installed. Text-to-speech will not be available.")
try:
    import gtts
    GTTS_AVAILABLE =True
    print("Google Text-to-Speech is available")
except ImportError:
    GTTS_AVAILABLE =False
    print("gtts not installed. Alternative TTS will not be available.")
import scipy.signal
try:
    import webrtcvad
    VAD_AVAILABLE =True
    print("Voice Activity Detection is available")
except ImportError:
    VAD_AVAILABLE =False
    print("webrtcvad not installed. VAD will not be available.")
try:
    import language_tool_python
    GRAMMAR_CHECKER_AVAILABLE =True
    print("Grammar checker is available")
except ImportError:
    GRAMMAR_CHECKER_AVAILABLE =False
    print("language_tool_python not installed. Grammar correction will not be available.")
SAMPLE_RATE =32000
VAD_FRAME_DURATION =30
VAD_AGGRESSIVENESS =3
CHANNELS =2
CHUNK_DURATION =3.0
grammar_correction_enabled =True
enhanced_english_grammar =True
IS_MACOS =platform.system()=='Darwin'
IS_WINDOWS =platform.system()=='Windows'
print("\n===== IMPORTANT TTS INSTALLATION GUIDE =====")
print("To make Text-to-Speech work properly, install BOTH options:")
print("1. pyttsx3:        pip install pyttsx3")
if IS_MACOS:
    print("2. Google TTS:     pip install gTTS")
    print("   (macOS users: built-in audio playback will be used)")
else:
    print("2. Google TTS:     pip install gTTS playsound")
print("At least one must be installed for TTS to work")
print("===========================================\n")
lang_source ='zh-CN'
lang_target ='en'
LANGUAGES ={
    'en':'English',
    'es':'Spanish',
    'fr':'French',
    'de':'German',
    'it':'Italian',
    'ja':'Japanese',
    'ko':'Korean',
    'pt':'Portuguese',
    'ru':'Russian',
    'zh-CN':'Chinese (Simplified)',
    'zh-TW':'Chinese (Traditional)',
    'ar':'Arabic',
    'hi':'Hindi',
    'nl':'Dutch',
    'pl':'Polish',
    'tr':'Turkish',
    'uk':'Ukrainian',
    'vi':'Vietnamese',
    'th':'Thai',
    'sv':'Swedish',
    'id':'Indonesian',
    'fa':'Persian',
    'he':'Hebrew',
    'cs':'Czech',
    'da':'Danish',
    'fi':'Finnish',
    'no':'Norwegian',
    'ro':'Romanian',
    'hu':'Hungarian',
    'el':'Greek',
}
LANG_EMOJIS ={
    'en':'🇺🇸',
    'es':'🇪🇸',
    'fr':'🇫🇷',
    'de':'🇩🇪',
    'it':'🇮🇹',
    'ja':'🇯🇵',
    'ko':'🇰🇷',
    'pt':'🇵🇹',
    'ru':'🇷🇺',
    'zh-CN':'🇨🇳',
    'zh-TW':'🇹🇼',
    'ar':'🇸🇦',
    'hi':'🇮🇳',
    'nl':'🇳🇱',
    'pl':'🇵🇱',
    'tr':'🇹🇷',
    'uk':'🇺🇦',
    'vi':'🇻🇳',
    'th':'🇹🇭',
    'sv':'🇸🇪',
    'id':'🇮🇩',
    'fa':'🇮🇷',
    'he':'🇮🇱',
    'cs':'🇨🇿',
    'da':'🇩🇰',
    'fi':'🇫🇮',
    'no':'🇳🇴',
    'ro':'🇷🇴',
    'hu':'🇭🇺',
    'el':'🇬🇷',
}
@lru_cache(maxsize=200)
def cached_translate(text,source_lang,target_lang):
    try:
        translator =GoogleTranslator(source=source_lang,target=target_lang)
        result =translator.translate(text)
        if result:
            return result
    except Exception as e:
        print(f"Primary translation failed: {e}")
    fallback_engines =[]
    if 'MyMemoryTranslator' in globals():
        fallback_engines.append(lambda:MyMemoryTranslator(source=source_lang,target=target_lang).translate(text))
    if 'LingueeTranslator' in globals():
        fallback_engines.append(lambda:LingueeTranslator(source=source_lang,target=target_lang).translate(text))
    for engine in fallback_engines:
        try:
            result =engine()
            if result:
                print("Used fallback translation engine")
                return result
        except Exception as e:
            print(f"Fallback translation failed: {e}")
    return f"{text} [TRANSLATION FAILED]"
recognizer =sr.Recognizer()
translator =GoogleTranslator(source=lang_source,target=lang_target)
recognizer.energy_threshold =250
recognizer.dynamic_energy_threshold =True
executor =concurrent.futures.ThreadPoolExecutor(max_workers=5)
audio_queue =queue.Queue()
translation_history =[]
is_listening =False
input_source ="microphone"
stream =None
debug_mode =False
show_pronunciation =True
def get_pronunciation(text,language):
    if not text:return ""
    if language =='zh-CN' or language =='zh-TW':
        print(f"Getting Chinese pronunciation for: {text}")
        if PINYIN_AVAILABLE:
            try:
                if not isinstance(text,str):text =str(text)
                print("Attempting to generate pinyin...")
                result =pinyin(text,style=Style.TONE)
                pronunciation =' '.join([item[0]for item in result])
                print(f"Generated pinyin: {pronunciation}")
                return pronunciation
            except Exception as e:
                print(f"Detailed pinyin error: {e}")
                try:
                    from pypinyin import lazy_pinyin
                    basic_pinyin =' '.join(lazy_pinyin(text))
                    print(f"Using basic pinyin instead: {basic_pinyin}")
                    return basic_pinyin
                except Exception as e2:
                    print(f"Basic pinyin also failed: {e2}")
                    return "[Pinyin unavailable]"
        else:
            print("pypinyin library not available for Chinese pronunciation")
            return "[Install pypinyin for pronunciation]"
    if language =='ja':
        print(f"Getting Japanese pronunciation for: {text}")
        if JAPANESE_AVAILABLE:
            try:
                kakasi =pykakasi.kakasi()
                result =kakasi.convert(text)
                romaji =" ".join([item['hepburn']for item in result])
                print(f"Generated Japanese romanization: {romaji}")
                return romaji
            except Exception as e:
                print(f"Japanese romanization error: {e}")
                return f"[Romanization error: {str(e)[:30]}...]"
        else:
            return "[Install pykakasi for Japanese pronunciation]"
    if language =='hi' or language =='sa':
        print(f"Getting Indic pronunciation for: {text}")
        if INDIC_AVAILABLE:
            try:
                result =indic_transliteration.sanscript.transliterate(text,indic_transliteration.sanscript.DEVANAGARI,indic_transliteration.sanscript.IAST)
                print(f"Generated Indic transliteration: {result}")
                return result
            except Exception as e:
                print(f"Indic transliteration error: {e}")
                return "[Transliteration error]"
        else:
            if TRANSLITERATE_AVAILABLE:
                try:
                    result =transliterate.translit(text,'hi',reversed=True)
                    return result
                except Exception as e:
                    print(f"Fallback transliteration error: {e}")
            return "[Install indic_transliteration for pronunciation]"
    if TRANSLITERATE_AVAILABLE:
        try:
            translit_langs ={
                'ru':'ru',
                'uk':'uk',
                'bg':'bg',
                'ka':'ka',
                'hy':'hy',
                'el':'el',
                'ar':'ar',
            }
            if language in translit_langs:
                import transliterate as transliterate_module
                language_code =translit_langs[language]
                available_langs =transliterate_module.get_available_language_codes()
                if language_code in available_langs:
                    result =transliterate_module.translit(text,language_code,reversed=True)
                else:
                    result =f"[{text}] (romanization not available for {LANGUAGES.get(language, language)})"
                print(f"Transliteration for {language}: {result}")
                return result
            else:
                return f"[Pronunciation guide not available for {LANGUAGES.get(language, language)}]"
        except Exception as e:
            print(f"Transliteration error for {language}: {e}")
            return f"[Transliteration unavailable for {LANGUAGES.get(language, language)}]"
    return ""
def log(message):
    if debug_mode:print(message)
def audio_callback(indata,frames,time,status):
    if status and debug_mode:print(f"Error: {status}",file=sys.stderr)
    audio_queue.put(indata.copy())
def capture_from_microphone():
    global is_listening
    log("Starting microphone capture...")
    while is_listening and input_source =="microphone":
        try:
            with sr.Microphone(sample_rate=SAMPLE_RATE)as source:
                recognizer.adjust_for_ambient_noise(source,duration=0.2)
                log("Listening to microphone...")
                try:
                    audio =recognizer.listen(source,timeout=3,phrase_time_limit=3)
                    executor.submit(process_audio_data,audio)
                except sr.WaitTimeoutError:
                    if debug_mode:print("Listening timeout-continuing to listen")
                    continue
        except Exception as e:
            if debug_mode:print(f"Microphone error: {e}")
            time.sleep(1)
def process_audio_data(audio):
    try:
        audio_np =np.frombuffer(audio.get_raw_data(),dtype=np.int16).astype(np.float32)/32767.0
        audio_np =apply_noise_reduction(audio_np)
        if VAD_AVAILABLE and not detect_speech_activity(audio_np):
            if debug_mode:print("No speech detected in audio sample")
            return
        processed_audio =sr.AudioData(
            (audio_np *32767).astype(np.int16).tobytes(),
            audio.sample_rate,
            audio.sample_width
        )
        try:
            text =recognizer.recognize_google(processed_audio,language=lang_source)
            if not text:
                raise sr.UnknownValueError("Empty result")
        except sr.UnknownValueError:
            try:
                print("Trying alternative recognition engine...")
                text =recognizer.recognize_sphinx(processed_audio,language=lang_source)
                print(f"Recognized with Sphinx: {text}")
            except:
                return
        except Exception as e:
            if debug_mode:print(f"Speech recognition error: {e}")
            return
        if text:
            log(f"Recognized: {text}")
            try:
                text =preprocess_text(text)
                translated_text =cached_translate(text,lang_source,lang_target)
                if grammar_correction_enabled and GRAMMAR_CHECKER_AVAILABLE:
                    translated_text =correct_grammar(translated_text,lang_target)
                result ={'original':text,'translated':translated_text,'timestamp':time.strftime('%H:%M:%S')}
                translation_history.append(result)
                if update_display:
                    if hasattr(update_display,'__self__')and hasattr(update_display.__self__,'after'):
                        update_display.__self__.after(0,lambda:update_display(result))
                    else:
                        update_display(result)
            except Exception as e:
                if debug_mode:print(f"Translation error: {e}")
    except Exception as e:
        if debug_mode:print(f"Audio processing error: {e}")
def preprocess_text(text):
    if not text:
        return text
    words =text.split()
    cleaned_words =[]
    for i,word in enumerate(words):
        if i ==0 or word.lower()!=words[i-1].lower():
            cleaned_words.append(word)
    text =" ".join(cleaned_words)
    text =text.replace(" ,",",").replace(" .",".").replace(" ?","?").replace(" !","!")
    for punct in [',','.','!','?',':',';']:
        while punct +punct in text:
            text =text.replace(punct +punct,punct)
    if text and text[0].isalpha()and not text[0].isupper():
        text =text[0].upper()+text[1:]
    while '  ' in text:
        text =text.replace('  ',' ')
    if text and text[-1].isalpha()and len(text)> 10:
        has_sentence_marker =any(marker in text for marker in ['.','!','?'])
        if not has_sentence_marker:
            text +='.'
    return text
def process_system_audio():
    log("Starting system audio processing...")
    while is_listening and input_source =="system":
        chunks =[]
        collected_duration =0
        target_duration =CHUNK_DURATION
        while collected_duration < target_duration and is_listening and input_source =="system":
            try:
                chunk =audio_queue.get(timeout=0.5)
                chunks.append(chunk)
                collected_duration +=len(chunk)/SAMPLE_RATE
            except queue.Empty:
                if chunks:break
                else:continue
        if not chunks:continue
        audio_data =np.concatenate(chunks)
        executor.submit(process_system_audio_chunk,audio_data)
def process_system_audio_chunk(audio_data):
    try:
        audio =sr.AudioData((audio_data *32767).astype(np.int16).tobytes(),SAMPLE_RATE,2)
        text =recognizer.recognize_google(audio,language=lang_source)
        if text:
            log(f"Recognized: {text}")
            try:
                translated_text =cached_translate(text,lang_source,lang_target)
                result ={'original':text,'translated':translated_text,'timestamp':time.strftime('%H:%M:%S')}
                translation_history.append(result)
                if update_display:
                    if hasattr(update_display,'__self__')and hasattr(update_display.__self__,'after'):update_display.__self__.after(0,lambda:update_display(result))
                    else:update_display(result)
            except Exception as e:
                if debug_mode:print(f"Translation error: {e}")
    except sr.UnknownValueError:pass
    except Exception as e:
        if debug_mode:print(f"Memory buffer processing failed, using file: {e}")
        process_system_audio_chunk_with_file(audio_data)
def process_system_audio_chunk_with_file(audio_data):
    with tempfile.NamedTemporaryFile(suffix=".wav",delete=False)as temp_wav:
        temp_filename =temp_wav.name
        with wave.open(temp_filename,'wb')as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio_data *32767).astype(np.int16).tobytes())
    try:
        with sr.AudioFile(temp_filename)as source:
            audio =recognizer.record(source)
            text =recognizer.recognize_google(audio,language=lang_source)
            if text:
                log(f"Recognized: {text}")
                try:
                    translated_text =cached_translate(text,lang_source,lang_target)
                    result ={'original':text,'translated':translated_text,'timestamp':time.strftime('%H:%M:%S')}
                    translation_history.append(result)
                    if update_display:
                        if hasattr(update_display,'__self__')and hasattr(update_display.__self__,'after'):update_display.__self__.after(0,lambda:update_display(result))
                        else:update_display(result)
                except Exception as e:
                    if debug_mode:print(f"Translation error: {e}")
    except sr.UnknownValueError:pass
    except Exception as e:
        if debug_mode:print(f"Error in processing: {e}")
    finally:
        try:os.unlink(temp_filename)
        except:pass
def start_system_capture():
    global stream
    try:
        print("Starting system audio capture...")
        if platform.system()=='Windows':
            try:
                devices =sd.query_devices()
                loopback_device =None
                for i,device in enumerate(devices):
                    if device['max_input_channels']> 0 and 'loopback' in device['name'].lower():
                        loopback_device =i
                        break
                if loopback_device is not None:
                    stream =sd.InputStream(callback=audio_callback,
                                         channels=CHANNELS,
                                         samplerate=SAMPLE_RATE,
                                         device=loopback_device)
                else:
                    stream =sd.InputStream(callback=audio_callback,
                                         channels=CHANNELS,
                                         samplerate=SAMPLE_RATE,
                                         device='default',
                                         extra_settings={'wasapi_exclusive':False,'loopback':True})
                stream.start()
                print("Windows system audio capture started successfully")
                return
            except Exception as win_error:
                print(f"Windows audio capture error: {win_error}")
                print("Falling back to default capture method")
        elif IS_MACOS:
            try:
                devices =sd.query_devices()
                blackhole_device =None
                for i,device in enumerate(devices):
                    device_name =device['name'].lower()
                    if device['max_input_channels']> 0 and any(name in device_name for name in ['blackhole','soundflower','loopback']):
                        blackhole_device =i
                        break
                if blackhole_device is not None:
                    stream =sd.InputStream(callback=audio_callback,
                                         channels=CHANNELS,
                                         samplerate=SAMPLE_RATE,
                                         device=blackhole_device)
                    stream.start()
                    print(f"macOS system audio capture started using virtual audio device: {devices[blackhole_device]['name']}")
                    return
                else:
                    print("No virtual audio device found on macOS. Cannot capture system audio.")
                    raise Exception("No virtual audio device found")
            except Exception as mac_error:
                print(f"macOS audio device setup failed: {mac_error}")
                raise
        stream =sd.InputStream(callback=audio_callback,channels=CHANNELS,samplerate=SAMPLE_RATE)
        stream.start()
        print("System audio capture started with default device")
    except Exception as e:
        print(f"Error starting system audio capture: {e}")
        raise
def stop_system_capture():
    global stream
    if stream is not None:
        try:
            if stream.active:stream.stop()
            stream.close()
            print("System audio capture stopped")
        except Exception as e:print(f"Error stopping system capture: {e}")
    stream=None
def toggle_input_source(new_source):
    global input_source,is_listening
    print(f"Switching input source from {input_source} to {new_source}")
    is_listening=False
    if input_source=="system":stop_system_capture()
    time.sleep(0.5)
    input_source=new_source
    is_listening=True
    if input_source=="microphone":threading.Thread(target=capture_from_microphone,daemon=True).start()
    else:
        try:
            start_system_capture()
            threading.Thread(target=process_system_audio,daemon=True).start()
        except Exception as e:
            print(f"Failed to start system audio: {e}")
            input_source="microphone"
            threading.Thread(target=capture_from_microphone,daemon=True).start()
    return input_source
def create_ui():
    global update_display
    root =tk.Tk()
    root.title("Advanced Translator")
    root.geometry("650x600")
    style =ttk.Style()
    def apply_theme():
        is_dark =detect_system_theme()
        if is_dark:
            root.configure(bg="#222222")
            translation_display.config(bg="#333333",fg="#ffffff",insertbackground="#ffffff")
            text_entry.config(bg="#333333",fg="#ffffff",insertbackground="#ffffff")
            style.configure("TFrame",background="#222222")
            style.configure("TLabel",background="#222222",foreground="#ffffff")
            style.configure("TButton",background="#444444")
            style.configure("TCheckbutton",background="#222222",foreground="#ffffff")
            style.configure("TLabelframe",background="#222222",foreground="#ffffff")
            style.configure("TLabelframe.Label",background="#222222",foreground="#ffffff")
        else:
            root.configure(bg="#f5f5f5")
            translation_display.config(bg="#ffffff",fg="#000000",insertbackground="#000000")
            text_entry.config(bg="#ffffff",fg="#000000",insertbackground="#000000")
            style.configure("TFrame",background="#f5f5f5")
            style.configure("TLabel",background="#f5f5f5",foreground="#000000")
            style.configure("TButton",background="#e0e0e0")
            style.configure("TCheckbutton",background="#f5f5f5",foreground="#000000")
            style.configure("TLabelframe",background="#f5f5f5",foreground="#000000")
            style.configure("TLabelframe.Label",background="#f5f5f5",foreground="#000000")
    def show_help():
        help_window =tk.Toplevel(root)
        help_window.title("Keyboard Shortcuts")
        help_window.geometry("400x300")
        help_window.transient(root)
        help_text ="""
            Keyboard Shortcuts:
            Ctrl+T:Translate text
            Ctrl+S:Save translation history
            Ctrl+C:Clear history
            Ctrl+M:Switch to microphone
            Ctrl+A:Switch to system audio
            F1:Show this help
        """
        help_label =ttk.Label(help_window,text=help_text,justify=tk.LEFT,font=("Segoe UI",10))
        help_label.pack(padx=20,pady=20)
        close_btn =ttk.Button(help_window,text="Close",command=help_window.destroy)
        close_btn.pack(pady=10)
    style.configure('Modern.TButton',font=('Segoe UI',10))
    style.configure('Language.TFrame',padding=10)
    frame =ttk.Frame(root,padding="10")
    frame.pack(fill=tk.BOTH,expand=True)
    header_frame =ttk.Frame(frame)
    header_frame.pack(fill=tk.X,pady=10)
    ttk.Label(header_frame,text="Advanced Translator",font=("Segoe UI",16,"bold")).pack(side=tk.LEFT,pady=5)
    lang_frame =ttk.Frame(frame,style='Language.TFrame')
    lang_frame.pack(fill=tk.X,pady=10)
    lang_source_var =tk.StringVar(value=lang_source)
    lang_target_var =tk.StringVar(value=lang_target)
    source_frame =ttk.Frame(lang_frame)
    source_frame.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=5)
    ttk.Label(source_frame,text="From:",font=("Segoe UI",10)).pack(side=tk.TOP,anchor=tk.W,pady=(0,5))
    language_list =[]
    for code,name in LANGUAGES.items():
        emoji =LANG_EMOJIS.get(code,'')
        language_list.append(f"{emoji} {name} ({code})")
    source_combo =ttk.Combobox(source_frame,textvariable=lang_source_var,width=25,font=("Segoe UI",9))
    source_combo['values']=language_list
    source_combo['state']='readonly'
    source_combo.pack(side=tk.TOP,fill=tk.X,expand=True)
    def get_lang_code_from_display(display_name):
        if not display_name:
            return 'en'
        import re
        match =re.search(r'\(([^)]+)\)$',display_name)
        if match:
            return match.group(1)
        return 'en'
    swap_frame =ttk.Frame(lang_frame)
    swap_frame.pack(side=tk.LEFT,fill=tk.Y,padx=5,pady=10)
    def swap_languages():
        src =lang_source_var.get()
        tgt =lang_target_var.get()
        lang_source_var.set(tgt)
        lang_target_var.set(src)
        update_lang_source()
        update_lang_target()
    swap_btn =ttk.Button(swap_frame,text="⇄",command=swap_languages,width=3)
    swap_btn.pack(side=tk.TOP,pady=10)
    target_frame =ttk.Frame(lang_frame)
    target_frame.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=5)
    ttk.Label(target_frame,text="To:",font=("Segoe UI",10)).pack(side=tk.TOP,anchor=tk.W,pady=(0,5))
    target_combo =ttk.Combobox(target_frame,textvariable=lang_target_var,width=25,font=("Segoe UI",9))
    target_combo['values']=language_list
    target_combo['state']='readonly'
    target_combo.pack(side=tk.TOP,fill=tk.X,expand=True)
    def update_lang_source(*args):
        global lang_source
        display_name =source_combo.get()
        lang_source =get_lang_code_from_display(display_name)
        print(f"Source language set to: {LANGUAGES.get(lang_source, lang_source)}")
        cached_translate.cache_clear()
    def update_lang_target(*args):
        global lang_target
        display_name =target_combo.get()
        lang_target =get_lang_code_from_display(display_name)
        print(f"Target language set to: {LANGUAGES.get(lang_target, lang_target)}")
        cached_translate.cache_clear()
    source_combo.bind('<<ComboboxSelected>>',update_lang_source)
    target_combo.bind('<<ComboboxSelected>>',update_lang_target)
    for i,item in enumerate(language_list):
        if f"({lang_source})" in item:
            source_combo.current(i)
        if f"({lang_target})" in item:
            target_combo.current(i)
    text_input_frame =ttk.LabelFrame(frame,text="Enter Text",padding=10)
    text_input_frame.pack(fill=tk.X,pady=10)
    text_entry =scrolledtext.ScrolledText(text_input_frame,wrap=tk.WORD,height=3,font=("Segoe UI",10))
    text_entry.pack(fill=tk.X,pady=5)
    button_frame =ttk.Frame(text_input_frame)
    button_frame.pack(fill=tk.X,pady=5)
    def translate_text():
        input_text =text_entry.get("1.0",tk.END).strip()
        if not input_text:return
        try:
            status_var.set("Translating...")
            root.update_idletasks()
            translated_text =cached_translate(input_text,lang_source,lang_target)
            if grammar_correction_enabled and GRAMMAR_CHECKER_AVAILABLE:
                translated_text =correct_grammar(translated_text,lang_target)
            result ={'original':input_text,'translated':translated_text,'timestamp':time.strftime('%H:%M:%S')}
            translation_history.append(result)
            update_display(result)
            if clear_after_var.get():
                text_entry.delete("1.0",tk.END)
            status_var.set("Ready")
        except Exception as e:
            print(f"Text translation error: {e}")
            status_var.set("Translation failed")
    translate_btn =ttk.Button(button_frame,text="Translate",
                              command=translate_text,style='Modern.TButton')
    translate_btn.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=5)
    clear_btn =ttk.Button(button_frame,text="Clear",
                          command=lambda:text_entry.delete("1.0",tk.END),style='Modern.TButton')
    clear_btn.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=5)
    clear_after_var =tk.BooleanVar(value=True)
    clear_check =ttk.Checkbutton(button_frame,text="Clear after translation",variable=clear_after_var)
    clear_check.pack(side=tk.RIGHT,padx=5)
    def on_key_press(event):
        if event.keysym =='Return' and not event.state & 0x0001:
            translate_text()
            return "break"
    text_entry.bind("<KeyPress>",on_key_press)
    voice_frame =ttk.LabelFrame(frame,text="Voice Translation",padding=10)
    voice_frame.pack(fill=tk.X,pady=10)
    status_frame =ttk.Frame(voice_frame)
    status_frame.pack(fill=tk.X,pady=5)
    status_var =tk.StringVar(value="Ready")
    status_label =ttk.Label(status_frame,textvariable=status_var,font=("Segoe UI",9))
    status_label.pack(side=tk.RIGHT)
    mic_frame =ttk.Frame(voice_frame)
    mic_frame.pack(fill=tk.X,pady=5)
    def switch_to_mic():
        current =toggle_input_source("microphone")
        status_var.set(f"Listening to microphone...")
        mic_btn.state(['disabled'])
        if has_system_audio():
            system_btn.state(['!disabled'])
    def switch_to_system():
        try:
            current =toggle_input_source("system")
            status_var.set(f"Capturing system audio...")
            system_btn.state(['disabled'])
            mic_btn.state(['!disabled'])
        except Exception as e:
            status_var.set(f"System audio error: {str(e)[:30]}")
            print(f"Error switching to system audio: {e}")
            mic_btn.state(['!disabled'])
    def has_system_audio():
        if platform.system()=='Windows':
            return True
        if IS_MACOS:
            devices =sd.query_devices()
            for device in devices:
                if device['max_input_channels']> 0:
                    device_name =device['name'].lower()
                    if any(name in device_name for name in ['blackhole','soundflower','loopback']):
                        return True
            return False
        return True
    mic_btn =ttk.Button(mic_frame,text="Use Microphone",command=switch_to_mic,
                        style='Modern.TButton')
    mic_btn.pack(side=tk.LEFT,padx=5,pady=5,fill=tk.X,expand=True)
    system_audio_available =has_system_audio()
    if system_audio_available:
        system_btn =ttk.Button(mic_frame,text="Capture System Audio",command=switch_to_system,
                              style='Modern.TButton')
        system_btn.pack(side=tk.LEFT,padx=5,pady=5,fill=tk.X,expand=True)
        if IS_MACOS:
            instruction_frame =ttk.Frame(voice_frame)
            instruction_frame.pack(fill=tk.X,pady=2)
            ttk.Label(instruction_frame,text="Note: System audio requires BlackHole",
                    foreground="#555555",font=("Segoe UI",9,"italic")).pack(side=tk.LEFT)
            download_btn =ttk.Button(
                instruction_frame,
                text="Download",
                command=lambda:open_url("https://github.com/ExistentialAudio/BlackHole/releases/latest"),
                width=10
            )
            download_btn.pack(side=tk.RIGHT,padx=5)
    if input_source =="microphone":
        mic_btn.state(['disabled'])
    elif input_source =="system" and system_audio_available:
        if 'system_btn' in locals():
            system_btn.state(['disabled'])
    display_frame =ttk.LabelFrame(frame,text="Translation History",padding=10)
    display_frame.pack(fill=tk.BOTH,expand=True,pady=10)
    translation_display =scrolledtext.ScrolledText(display_frame,wrap=tk.WORD,font=("Segoe UI",10))
    translation_display.pack(fill=tk.BOTH,expand=True)
    translation_display.config(state=tk.DISABLED)
    debug_frame =ttk.LabelFrame(frame,text="Debug Messages")
    debug_display =scrolledtext.ScrolledText(debug_frame,wrap=tk.WORD,height=4)
    debug_display.pack(fill=tk.BOTH,expand=True)
    debug_display.config(state=tk.DISABLED)
    class TextRedirector:
        def __init__(self,text_widget):self.text_widget=text_widget
        def write(self,string):
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END,string)
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
        def flush(self):pass
    sys.stdout =TextRedirector(debug_display)
    def update_ui(result):
        translation_display.config(state=tk.NORMAL)
        source_emoji =LANG_EMOJIS.get(lang_source,'🌐')
        target_emoji =LANG_EMOJIS.get(lang_target,'🌐')
        timestamp_line =f"[{result['timestamp']}]\n"
        source_line =f"{source_emoji} {result['original']}\n"
        target_line =f"{target_emoji} {result['translated']}\n"
        translation_display.insert(tk.END,timestamp_line +source_line +target_line +"\n")
        if TTS_AVAILABLE or GTTS_AVAILABLE:
            button_frame =ttk.Frame(translation_display)
            if TTS_AVAILABLE or GTTS_AVAILABLE:
                tts_source_btn =ttk.Button(
                    button_frame,
                    text=f"🔊 {source_emoji}",
                    command=lambda:speak_text(result['original'],lang_source),
                    width=5
                )
                tts_source_btn.pack(side=tk.LEFT,padx=2)
            if TTS_AVAILABLE or GTTS_AVAILABLE:
                tts_target_btn =ttk.Button(
                    button_frame,
                    text=f"🔊 {target_emoji}",
                    command=lambda:speak_text(result['translated'],lang_target),
                    width=5
                )
                tts_target_btn.pack(side=tk.LEFT,padx=2)
            translation_display.window_create(tk.END,window=button_frame)
            translation_display.insert(tk.END,"\n\n")
        else:
            translation_display.insert(tk.END,"\n")
        translation_display.see(tk.END)
        translation_display.config(state=tk.DISABLED)
    def clear_history():
        translation_display.config(state=tk.NORMAL)
        translation_display.delete(1.0,tk.END)
        translation_display.config(state=tk.DISABLED)
        translation_history.clear()
    update_display =update_ui
    def on_closing():
        global is_listening
        is_listening =False
        if input_source =="system":
            stop_system_capture()
        save_settings()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW",on_closing)
    actions_frame =ttk.Frame(frame)
    actions_frame.pack(fill=tk.X,pady=5)
    save_btn =ttk.Button(actions_frame,text="Save History",
                         command=save_translation_history,style='Modern.TButton')
    save_btn.pack(side=tk.LEFT,padx=5)
    clear_btn =ttk.Button(actions_frame,text="Clear History",
                          command=clear_history,style='Modern.TButton')
    clear_btn.pack(side=tk.LEFT,padx=5)
    help_btn =ttk.Button(actions_frame,text="Keyboard Shortcuts",
                         command=show_help,style='Modern.TButton')
    help_btn.pack(side=tk.RIGHT,padx=5)
    def setup_keyboard_shortcuts():
        root.bind("<Control-t>",lambda e:translate_text())
        root.bind("<Control-s>",lambda e:save_translation_history())
        root.bind("<Control-c>",lambda e:clear_history())
        root.bind("<F1>",lambda e:show_help())
        root.bind("<Control-m>",lambda e:switch_to_mic()if not mic_btn.instate(['disabled'])else None)
        if system_audio_available:
            root.bind("<Control-a>",lambda e:switch_to_system()if not (hasattr(locals(),'system_btn')and system_btn.instate(['disabled']))else None)
    setup_keyboard_shortcuts()
    apply_theme()
    return root
def toggle_debug(state):
    global debug_mode
    debug_mode =state
    print(f"Debug mode {'enabled' if debug_mode else 'disabled'}")
def save_translation_history():
    filename =tk.filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files","*.txt"),("All files","*.*")],
        title="Save Translation History"
    )
    if not filename:
        return
    try:
        with open(filename,'w',encoding='utf-8')as f:
            for item in translation_history:
                source_emoji =LANG_EMOJIS.get(lang_source,'🌐')
                target_emoji =LANG_EMOJIS.get(lang_target,'🌐')
                f.write(f"[{item['timestamp']}]\n")
                f.write(f"{source_emoji}: {item['original']}\n")
                f.write(f"{target_emoji}: {item['translated']}\n\n")
        print(f"Successfully saved translations to {filename}")
    except Exception as e:
        print(f"Error saving file: {e}")
def open_url(url):
    import webbrowser
    webbrowser.open(url)
def save_settings():
    settings ={
        'source_language':lang_source,
        'target_language':lang_target,
        'show_pronunciation':show_pronunciation,
        'debug_mode':debug_mode,
        'input_source':input_source,
        'grammar_correction_enabled':grammar_correction_enabled,
        'enhanced_english_grammar':enhanced_english_grammar
    }
    try:
        with open('translator_settings.json','w')as f:json.dump(settings,f)
        print("Settings saved")
    except Exception as e:
        print(f"Failed to save settings: {e}")
def main():
    load_settings()
    root =create_ui()
    global is_listening
    is_listening =True
    toggle_input_source(input_source)
    root.mainloop()
    executor.shutdown(wait=False)
def speak_text(text,language):
    if not text.strip():
        print("No text to speak")
        return
    print(f"Speaking text in {language}: {text}")
    if GTTS_AVAILABLE:
        try:
            with tempfile.NamedTemporaryFile(delete=False,suffix='.mp3')as fp:
                temp_filename =fp.name
            lang_code =language.split('-')[0]
            tts =gtts.gTTS(text=text,lang=lang_code)
            tts.save(temp_filename)
            def play_audio():
                try:
                    if IS_MACOS:
                        import subprocess
                        subprocess.call(['afplay',temp_filename])
                    else:
                        try:
                            import playsound
                            playsound.playsound(temp_filename)
                        except ImportError:
                            print("playsound not available, trying alternative playback methods")
                            pass
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                except Exception as e:
                    print(f"Error playing sound: {e}")
            threading.Thread(target=play_audio,daemon=True).start()
            return
        except Exception as e:
            print(f"Google TTS error: {e}")
    if TTS_AVAILABLE:
        try:
            import subprocess
            script_template ="""
                import pyttsx3
                engine =pyttsx3.init()
                engine.say('''{text}''')
                engine.runAndWait()
            """
            escaped_text =text.replace("'","\\'").replace('"','\\"')
            script_content =script_template.format(text=escaped_text)
            with tempfile.NamedTemporaryFile(mode='w',suffix='.py',delete=False)as f:
                script_path =f.name
                f.write(script_content)
            subprocess.Popen([sys.executable,script_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            def cleanup():
                try:
                    os.unlink(script_path)
                except:
                    pass
            timer =threading.Timer(10.0,cleanup)
            timer.daemon =True
            timer.start()
        except Exception as e:
            print(f"Fallback TTS error: {e}")
    else:
        print("Text-to-speech is not available. Please install pyttsx3 or gtts+playsound.")
def apply_noise_reduction(audio_data):
    try:
        if len(audio_data)==0 or np.max(np.abs(audio_data))< 1e-6:
            if debug_mode:print("Audio data too quiet for noise reduction")
            return audio_data
        rms =np.sqrt(np.mean(audio_data**2))
        threshold =0.1 *rms
        audio_data =np.where(np.abs(audio_data)< threshold,0,audio_data)
        if debug_mode:print("Applied simple noise reduction")
        return audio_data
    except Exception as e:
        print(f"Error in noise reduction: {e}")
        return audio_data
def detect_speech_activity(audio_data,sample_rate=SAMPLE_RATE):
    if not VAD_AVAILABLE:
        return True
    try:
        audio_data_16bit =(audio_data *32767).astype(np.int16)
        valid_rates =[8000,16000,32000,48000]
        vad_rate =min(valid_rates,key=lambda x:abs(x -sample_rate))
        if sample_rate !=vad_rate:
            print(f"Resampling from {sample_rate} to {vad_rate} for VAD")
            ratio =sample_rate //vad_rate
            audio_data_16bit =audio_data_16bit[::ratio]
        frame_size =int(vad_rate *(VAD_FRAME_DURATION /1000))
        num_frames =len(audio_data_16bit)//frame_size
        speech_frames =0
        vad =webrtcvad.Vad(VAD_AGGRESSIVENESS)
        for i in range(num_frames):
            frame =audio_data_16bit[i *frame_size:(i +1)*frame_size]
            if vad.is_speech(frame.tobytes(),vad_rate):
                speech_frames +=1
        return speech_frames /max(1,num_frames)> 0.1
    except Exception as e:
        print(f"VAD error: {e}")
        return True
def correct_grammar(text,language):
    if not grammar_correction_enabled or not GRAMMAR_CHECKER_AVAILABLE:
        return text
    try:
        if language =='en' and enhanced_english_grammar:
            lang_code ='en-US'
            grammar_tool =language_tool_python.LanguageTool(lang_code)
            matches =grammar_tool.check(text)
            corrected =language_tool_python.utils.correct(text,matches)
            corrected =post_process_english(corrected)
            if corrected !=text:
                print(f"Grammar corrected: '{text}' → '{corrected}'")
            return corrected
        else:
            lang_code =map_language_code(language)
            grammar_tool =language_tool_python.LanguageTool(lang_code)
            matches =grammar_tool.check(text)
            corrected =language_tool_python.utils.correct(text,matches)
            if corrected !=text:
                print(f"Grammar corrected: '{text}' → '{corrected}'")
            return corrected
    except Exception as e:
        print(f"Grammar correction error: {e}")
        return text
def post_process_english(text):
    if not text:
        return text
    sentences =[]
    for sentence in text.split('. '):
        if sentence and not sentence[0].isupper()and sentence[0].isalpha():
            sentences.append(sentence[0].upper()+sentence[1:])
        else:
            sentences.append(sentence)
    text ='. '.join(sentences)
    for punct in ['.',',','!','?',':',';']:
        text =text.replace(f"{punct}",f"{punct} ")
    while '  ' in text:
        text =text.replace('  ',' ')
    text =re.sub(r'\bi\b','I',text)
    contractions ={
        'dont':"don't",
        'cant':"can't",
        'wont':"won't",
        'isnt':"isn't",
        'didnt':"didn't",
        'wouldnt':"wouldn't",
        'shouldnt':"shouldn't",
        'couldnt':"couldn't",
        'hasnt':"hasn't",
        'havent':"haven't",
        'hadnt':"hadn't",
        'ive':"I've",
        'youve':"you've",
        'weve':"we've",
        'theyve':"they've",
        'im':"I'm",
        'youre':"you're",
        'hes':"he's",
        'shes':"she's",
        'theyre':"they're",
        'were':"we're",
        'ill':"I'll",
        'youll':"you'll",
        'hell':"he'll",
        'shell':"she'll",
        'theyll':"they'll",
        'well':"we'll"
    }
    words =text.split()
    for i,word in enumerate(words):
        lower_word =word.lower()
        if lower_word in contractions:
            if word[0].isupper():
                first_char =contractions[lower_word][0].upper()
                rest =contractions[lower_word][1:]
                words[i]=first_char +rest
            else:
                words[i]=contractions[lower_word]
    return ' '.join(words)
def map_language_code(lang_code):
    mapping ={
        'en':'en-US',
        'es':'es',
        'fr':'fr',
        'de':'de-DE',
        'it':'it',
        'pt':'pt-PT',
        'ru':'ru',
        'nl':'nl',
    }
    return mapping.get(lang_code,'en-US')
def detect_system_theme():
    try:
        if IS_MACOS:
            import subprocess
            cmd ="defaults read -g AppleInterfaceStyle"
            result =subprocess.run(cmd,shell=True,check=False,capture_output=True,text=True)
            return result.stdout.strip()=="Dark"
        elif IS_WINDOWS:
            import winreg
            try:
                registry =winreg.ConnectRegistry(None,winreg.HKEY_CURRENT_USER)
                key =winreg.OpenKey(registry,r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value,_ =winreg.QueryValueEx(key,"AppsUseLightTheme")
                return value ==0
            except Exception as e:
                print(f"Error detecting Windows theme: {e}")
                return False
        return False
    except Exception as e:
        print(f"Error detecting system theme: {e}")
        return False
def load_settings():
    global lang_source,lang_target,show_pronunciation,debug_mode,input_source,grammar_correction_enabled,enhanced_english_grammar
    try:
        if os.path.exists('translator_settings.json'):
            with open('translator_settings.json','r')as f:
                settings =json.load(f)
            lang_source =settings.get('source_language',lang_source)
            lang_target =settings.get('target_language',lang_target)
            show_pronunciation =settings.get('show_pronunciation',show_pronunciation)
            debug_mode =settings.get('debug_mode',debug_mode)
            input_source =settings.get('input_source',input_source)
            grammar_correction_enabled =settings.get('grammar_correction_enabled',grammar_correction_enabled)
            enhanced_english_grammar =settings.get('enhanced_english_grammar',enhanced_english_grammar)
            print("Settings loaded")
    except Exception as e:
        print(f"Failed to load settings: {e}")
if __name__=="__main__":update_display=None; main()