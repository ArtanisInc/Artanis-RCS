<h1 align="center">Artanis RCS</h1>

<p align="center"><strong>Advanced recoil compensation system for Counter-Strike 2 with automatic weapon detection</strong></p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" /></a>
  <a href="https://www.microsoft.com/windows"><img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" /></a>
  <a href="#license--disclaimer"><img src="https://img.shields.io/badge/license-Educational%20Use-orange.svg" /></a>
</p>

> [!CAUTION]
> This software is provided for educational and research purposes only.
> Using automated input assistance in Counter-Strike 2 may violate Valve's Terms of Service and could result in a VAC (Valve Anti-Cheat) ban.
> Use at your own risk. The developers are not responsible for any consequences.

## 🎯 **Key Features**

🔫 **Multi-Weapon Support**
* 16 precise recoil patterns (CSV format)
* Human-friendly recoil compensation

🎮 **GSI (Game State Integration)**
* Automatic weapon detection (CS2)
* Instant pattern switching

🖥️ **Advanced User Interface**
* Modern, intuitive PyQt5 GUI
* Recoil pattern visualization
* Live system status and configuration management

🔊 **Audio Feedback**
* Text-to-speech (TTS) for system events
* Voice alerts for critical events and weapon changes

---

## 🛠️ **Technical Architecture**

```
artanis-rcs/
├── main.py                          # Application entry point with GSI integration
├── config.json                      # Main configuration file
├── requirements.txt                 # Python dependencies
├── start.bat                        # Windows startup script with dependency management
├── core/                            # Core system components
│   ├── models/                      # Data models and structures
│   │   ├── player_state.py          # Game state representation
│   │   ├── weapon.py                # Weapon data model
│   │   └── recoil_data.py           # Recoil pattern data structure
│   └── services/                    # Business logic services
│       ├── config_service.py        # Configuration management
│       ├── recoil_service.py        # Core recoil compensation logic
│       ├── gsi_service.py           # Game State Integration server
│       ├── weapon_detection_service.py # Automatic weapon detection
│       ├── input_service.py         # Mouse input control (SendInput API)
│       ├── hotkey_service.py        # Global keyboard hotkey handling
│       ├── tts_service.py           # Text-to-speech feedback system
│       └── timing_service.py        # Precise timing control
├── ui/                              # User interface components
│   ├── views/                       # Main application views
│   │   ├── main_window.py           # Primary application window
│   │   ├── config_tab.py            # Configuration interface
│   │   ├── visualization_tab.py     # Pattern visualization
│   │   └── styles.py                # UI styling and themes
│   └── widgets/                     # Custom UI components
│       └── pattern_visualizer.py    # Recoil pattern display widget
├── patterns/                        # Recoil pattern data (CSV format)
│   ├── ak47.csv                     # AK-47 spray pattern
│   ├── m4a4.csv                     # M4A4 spray pattern
│   ├── m4a1.csv                     # M4A1-S spray pattern
│   └── [13 additional weapon patterns]
└── data/                            # Data repositories and persistence
    └── config_repository.py         # Configuration file management and pattern data loading and parsing
```

---

## 🔧 **Installation & Setup**

### **System Requirements**
- **Operating System**: Windows 10/11 (required for pywin32)
- **Python**: Version 3.9 or higher
- **Counter-Strike 2**: Latest version with GSI capability

### **Dependencies**
- **PyQt5**: Modern GUI framework
- **matplotlib**: Pattern visualization and analysis
- **numpy**: Mathematical calculations and array operations
- **pywin32**: Windows API integration for input simulation

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

   Or use the provided batch script:
   ```bash
   start.bat
   ```

3. **Launch the Application**
   ```bash
   python main.py
   ```

   Or double-click `start.bat` for automated dependency management.

---

## 📋 **Supported Weapons**

The system includes precise recoil patterns for 16 automatic weapons:

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
| **Pistols**       | CZ75-Auto    | `cz75.csv`     |

---

## ⚙️ **Configuration Guide**

### **Core Settings (`config.json`)**

#### **Game Sensitivity**
```json
"game_sensitivity": 1.08
```
Set this to match your in-game sensitivity setting for accurate compensation.

#### **Feature Toggles**
```json
"features": {
    "tts_enabled": true          // Enable/disable audio feedback
}
```

#### **GSI Configuration**
```json
"gsi": {
    "enabled": true,                    // Master GSI toggle
    "auto_weapon_switch": true,         // Automatic weapon detection
    "auto_rcs_control": true,           // Automatic RCS activation
    "low_ammo_threshold": 5,            // Low ammo warning threshold
    "server_host": "127.0.0.1",         // GSI server address
    "server_port": 59873,               // GSI server port
    "update_rate_limit": 0.1,           // Update frequency limit
    "transition_delay": 0.2             // Weapon switch delay
}
```

#### **Hotkey Bindings**
```json
"hotkeys": {
    "exit": "END",                      // Emergency exit
    "toggle_recoil": "INSERT",          // Toggle compensation on/off
    "toggle_weapon_detection": "HOME"   // Toggle automatic detection
    // Other weapons activation keys...
}
```

#### **Weapon Parameters**
Each weapon includes customizable parameters:
```json
{
    "name": "ak47",              // Internal weapon identifier
    "display_name": "AK-47",     // UI display name
    "length": 30,                // Pattern length (bullets)
    "multiple": 6,               // Compensation multiplier
    "sleep_divider": 6,          // Timing divisor
    "sleep_suber": -0.1          // Timing adjustment
}
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **GSI Connection Problems**
- Verify GSI configuration file exists in CS2 config directory
- Check that CS2 is running and GSI is enabled
- Confirm server port (59873) is not blocked by firewall

#### **Hotkey Conflicts**
- Check for conflicting applications using the same keys
- Modify hotkey bindings in `config.json` or via the UI
- Restart application after configuration changes

#### **TTS System Issues**
- Verify Windows Speech Platform components
- Test TTS by toggling `tts_enabled` setting or via the UI

#### **Sensitivity Calibration**
- Match `game_sensitivity` exactly to CS2 setting
- Adjust weapon-specific multipliers if needed

### **Log Files**
- `recoil_system.log`: Main application log
- `startup.log`: Startup script log (from start.bat)

---

## 🤝 **Contributing**

### **Code Style Standards**
- Follow PEP 8 Python style guidelines
- Use type hints for function parameters and returns
- Maintain comprehensive docstrings
- Include error handling for all external dependencies

### **Pull Request Process**
1. Fork the repository
2. Create feature branch from main
3. Implement changes with proper testing
4. Update documentation as needed
5. Submit pull request with detailed description

---

## 🆘 **Support & Resources**

### **Issue Reporting**
When reporting issues, please include:
- Operating system version
- Python version
- CS2 game version
- Complete error logs
- Steps to reproduce the problem

### **GSI Documentation**
- [Valve Developer Community - Game State Integration](https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive_Game_State_Integration)
- [CS2 GSI Implementation](https://github.com/antonpup/CounterStrike2GSI)

---

## 📄 **License & Attribution**

### **License**
This project is released under the MIT License with the following additional terms:

**EDUCATIONAL USE ONLY**: This software is intended solely for educational and research purposes. Any use in violation of game Terms of Service is strictly prohibited and not endorsed by the developers.

### **Pattern and Algorithms Data Sources**
- Recoil patterns derived from CS2 chinese community.
- Algorithms derived from this project [ NewTennng / csgoPress-the-gun](https://github.com/NewTennng/csgoPress-the-gun/tree/main)
