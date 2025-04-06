# Translator

A real-time translation application that translates text and speech between 25+ languages.

## Features

- Translate between 25+ languages with a single click
- Microphone input support
- System audio capture (Windows native, macOS with BlackHole)
- Text-to-Speech playback
- Grammar correction
- Save translation history

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. For macOS:
   - Download and install [BlackHole](https://github.com/ExistentialAudio/BlackHole/releases/latest)
   - Set BlackHole as your output device in System Preferences
   - The app will automatically detect BlackHole when installed

## Usage

Run the application:

```bash
python translator.py
```

### Key Features

- **Text Translation**: Type text in the input box and click "Translate"
- **Voice Translation**: Choose microphone for direct speech or system audio to translate from your computer
- **Language Swap**: Use the swap button (⇄) to quickly reverse translation direction
- **Text-to-Speech**: Click the speaker icons to hear the original or translated text
- **Save History**: Save your translation history as a text file

### Keyboard Shortcuts

- **Ctrl+T**: Translate text
- **Ctrl+S**: Save translation history
- **Ctrl+C**: Clear history
- **Ctrl+M**: Switch to microphone
- **Ctrl+A**: Switch to system audio
- **F1**: Show keyboard shortcuts

## Notes

- Windows users can capture system audio without additional software
- macOS users need BlackHole for system audio capture
- The application automatically detects available audio capture methods for your system
