<h1 align="center">Artanis RCS</h1>

<p align="center"><strong>Advanced recoil compensation system for Counter-Strike 2 with automatic weapon detection</strong></p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.13+-blue.svg" /></a>
  <a href="https://www.microsoft.com/windows"><img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" /></a>
  <a href="https://github.com/ArtanisInc/Artanis-RCS/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-orange.svg" /></a>
</p>
<p align="center">
  <img src="https://i.imgur.com/TcAqjOp.png" alt="Artanis RCS Logo" width="500"/>
</p>

> [!CAUTION]
> This software is provided for educational and research purposes only.
> Using automated input assistance in Counter-Strike 2 may violate Valve's Terms of Service and could result in a VAC (Valve Anti-Cheat) ban.
> Use at your own risk. The developers are not responsible for any consequences.

## 🎯 **Key Features**

🔫 **Multi-Weapon Support**
* 17 precise recoil patterns (CSV format)
* Human-friendly recoil compensation
* Jitter timing and movement customization per weapon

🎮 **GSI (Game State Integration)**
* Automatic weapon detection
* Automatic RCS activation based on game state
* Instant pattern switching

🖥️ **Advanced User Interface**
* Modern, intuitive PySide6 GUI with qdarktheme
* Recoil pattern visualization
* Live system status and configuration management
* Follow RCS overlay for visual recoil tracking

🔊 **Audio Feedback**
* Text-to-speech (TTS) for system events

💣 **Bomb Timer System**
* Real-time bomb countdown display with circular progress overlay

🎯 **Auto-Accept System**
* Automatic match acceptance via console monitoring and screen detection


## 🛠️ **Technical Architecture**

```
artanis-rcs/
├── main.py                          # Application entry point with GSI integration and service orchestration
├── config.json                      # Main configuration file
├── requirements.txt                 # Python dependencies
├── start.bat                        # Windows startup script with dependency management
├── core/                            # Core system components
│   ├── models/                      # Data models and structures
│   │   ├── player_state.py          # Game state representation and player data
│   │   ├── weapon.py                # Weapon data model and properties
│   │   ├── recoil_data.py           # Recoil pattern data structure and management
│   │   └── __init__.py              # Models package initialization
│   └── services/                    # Business logic services
│       ├── config_service.py        # Configuration management and validation
│       ├── recoil_service.py        # Core recoil compensation logic and pattern execution
│       ├── gsi_service.py           # Game State Integration server and CS2 communication
│       ├── weapon_detection_service.py # Automatic weapon detection and switching logic
│       ├── input_service.py         # Mouse input control (SendInput API) and cursor management
│       ├── hotkey_service.py        # Global keyboard hotkey handling and system control
│       ├── tts_service.py           # Text-to-speech feedback system and voice notifications
│       ├── bomb_timer_service.py    # Bomb countdown timer, defuse alerts, and overlay management
│       ├── timing_service.py        # Precise timing control and pattern synchronization
│       ├── auto_accept_service.py   # Automatic match acceptance with multi-modal detection
│       ├── console_log_service.py   # Real-time CS2 console log monitoring and parsing
│       ├── screen_capture_service.py # Screen capture, color detection, and window management
│       └── __init__.py              # Services package initialization
├── ui/                              # User interface components
│   ├── views/                       # Main application views
│   │   ├── main_window.py           # Primary application window and tab management
│   │   ├── config_tab.py            # Configuration interface and settings management
│   │   ├── visualization_tab.py     # Pattern visualization and analysis tools
│   │   └── __init__.py              # Views package initialization
│   └── widgets/                     # Custom UI components
│       ├── pattern_visualizer.py    # Interactive recoil pattern display widget
│       ├── bomb_timer_overlay.py    # Bomb countdown overlay widget with progress indicator
│       ├── follow_rcs_overlay.py    # Visual recoil tracking overlay widget
│       └── __init__.py              # Widgets package initialization
├── patterns/                        # Recoil pattern data (CSV format)
│   ├── ak47.csv                     # AK-47 spray pattern data
│   ├── m4a4.csv                     # M4A4 spray pattern data
│   ├── m4a1.csv                     # M4A1-S spray pattern data
│   └── [14 additional weapon patterns] # Complete weapon pattern library
└── data/                            # Data repositories and persistence
    ├── config_repository.py         # Configuration file management, pattern loading, and data persistence
    └── __init__.py                  # Data package initialization
```


## 🔧 **Installation & Setup**

### **System Requirements**
- **Operating System**: Windows 10/11 (required for pywin32 and screen capture)
- **Python**: Version 3.13 or higher

### **Dependencies**
- **PySide6**: Modern GUI framework for user interface
- **PyQtDarkTheme**: A flat dark theme for PySide and PyQt
- **matplotlib**: Pattern visualization and mathematical plotting
- **numpy**: Mathematical calculations and array operations
- **pywin32**: Windows API integration for input simulation and window management
- **DXcam**: Image processing for screen capture and analysis
- **QtAwesome**: Font Awesome for Qt Applications

### **Installation Steps**

1. **Clone the Repository**
   ```bash
   git clone https://github.com/ArtanisInc/artanis-rcs.git
   cd artanis-rcs
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   Or use the provided batch script for automated setup:
   ```bash
   start.bat
   ```

3. **Ensure console debug logging is enabled in CS2**
   ```bash
   -conclearlog -condebug
   ```

4. **Launch the Application**
   ```bash
   python main.py
   ```

   Or double-click `start.bat` for automated dependency management and startup.


## 📋 **Supported Weapons**

The system includes precise recoil patterns for 17 automatic weapons:

| Category          | Weapon        | CSV File       |
|-------------------|--------------|----------------|
| **Rifles**        | AK-47        | `ak47.csv`     |
|                   | M4A4         | `m4a4.csv`     |
|                   | M4A1-S       | `m4a1.csv`     |
|                   | Galil AR     | `galil.csv`    |
|                   | FAMAS        | `famas.csv`    |
|                   | SG 553       | `sg553.csv`    |
|                   | AUG          | `aug.csv`      |
| **SMGs**          | P90          | `p90.csv`      |
|                   | PP-Bizon     | `bizon.csv`    |
|                   | UMP-45       | `ump45.csv`    |
|                   | MAC-10       | `mac10.csv`    |
|                   | MP5-SD       | `mp5sd.csv`    |
|                   | MP7          | `mp7.csv`      |
|                   | MP9          | `mp9.csv`      |
| **Heavy**         | M249         | `m249.csv`     |
|                   | NEGEV        | `negev.csv`    |
| **Pistols**       | CZ75-AUTO    | `cz75.csv`     |

---

## ⚙️ **Configuration Guide**

### **Core Settings (`config.json`)**

#### **Game Sensitivity**
```json
"game_sensitivity": 1.08
```

#### **Feature Toggles**
```json
"features": {
    "tts_enabled": true,                # Toggle audio feedback system
    "bomb_timer_enabled": false,         # Toggle bomb timer overlay
    "auto_accept_enabled": false,        # Toggle automatic match acceptance
    "follow_rcs_enabled": false         # Toggle visual recoil tracking overlay
}
```

#### **Follow RCS Overlay Configuration**
```json
"follow_rcs": {
    "dot_size": 3,                      # Size of the tracking dot in pixels
    "color": [0, 0, 255, 255]           # RGBA color values (red, green, blue, alpha)
}
```

#### **GSI Configuration**
```json
"gsi": {
    "enabled": true,                    # Master GSI toggle
    "low_ammo_threshold": 5,            # Low ammunition warning threshold
    "server_host": "127.0.0.1",         # GSI server listening address
    "server_port": 59873               # GSI server port (must match CS2 config)
}
```

#### **Hotkey Bindings**
```json
"hotkeys": {
    "exit": "END",                      # Emergency application exit
    "toggle_recoil": "INSERT",          # Toggle recoil compensation on/off
    "toggle_weapon_detection": "HOME",  # Toggle automatic weapon detection
    // ... additional weapon bindings
    "ak47": "F1",
    "m4a4": "F2",
    "m4a1": "F3"
}
```

#### **Weapon Parameters**
Each weapon includes customizable compensation parameters:
```json
{
    "name": "ak47",              # Internal weapon identifier
    "display_name": "AK-47",     # Human-readable weapon name
    "length": 30,                # Recoil pattern length (bullets)
    "multiple": 6,               # Compensation intensity multiplier
    "sleep_divider": 6.0,        # Timing calculation divisor
    "sleep_suber": -0.1,         # Fine-tuning timing adjustment
    "jitter_timing": 0.0,        # Random timing variation (+/- milliseconds)
    "jitter_movement": 0.0       # Random movement variation (+/- percentage)
}
```


## 🚨 **Troubleshooting**

### **Common Issues**

#### **GSI Connection Problems**
- **Symptoms**: No automatic weapon detection, GSI status shows "Disconnected"
- **Solutions**:
  - Verify GSI configuration file exists in CS2 config directory `Counter-Strike Global Offensive/game/csgo/cfg/gamestate_integration_rcs`
  - Confirm server port (59873) is not blocked by firewall
  - Restart both CS2 and Artanis RCS after configuration changes

#### **Auto-Accept Not Working**
- **Symptoms**: Matches not being accepted automatically
- **Solutions**:
  - Verify CS2 console debug logging is enabled `-conclearlog -condebug`
  - Check console log file path `Counter-Strike Global Offensive/game/csgo/console.log`

#### **Hotkey Conflicts**
- **Symptoms**: Hotkeys not responding or conflicting with other applications
- **Solutions**:
  - Check for conflicting applications using the same key combinations
  - Modify hotkey bindings in `config.json` or via the Configuration tab
  - Run application as Administrator for global hotkey access
  - Restart application after configuration changes

#### **TTS System Issues**
- **Symptoms**: No voice feedback or audio errors
- **Solutions**:
  - Verify Windows Speech Platform components are installed
  - Check system audio settings and default playback device
  - Restart Windows Speech Service if necessary

#### **Sensitivity Calibration**
- **Symptoms**: Recoil compensation too strong/weak or inaccurate
- **Solutions**:
  - Match `game_sensitivity` exactly to your CS2 in-game sensitivity
  - Adjust weapon-specific `multiple` values for fine-tuning

### **Log Files and Debugging**
- **Logs**: `recoil_system.log` - Main application events and errors
- **Debug Mode**: Enable verbose logging by setting `level=logging.DEBUG` in `main.py`


## 📄 **License & Attribution**

### **License**
This project is released under the [MIT License](https://github.com/ArtanisInc/Artanis-RCS/blob/main/LICENSE) with the following additional terms:

### **Pattern and Algorithms Data Sources**
- Recoil patterns derived from CS2 chinese community.
- Algorithms derived from this project [ NewTennng / csgoPress-the-gun](https://github.com/NewTennng/csgoPress-the-gun/tree/main)
