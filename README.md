<h1 align="center">Artanis RCS</h1>

<p align="center"><strong>Advanced recoil compensation system for Counter-Strike 2 with automatic weapon detection</strong></p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" /></a>
  <a href="https://www.microsoft.com/windows"><img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" /></a>
  <a href="#license--disclaimer"><img src="https://img.shields.io/badge/license-Educational%20Use-orange.svg" /></a>
</p>

## ⚠️ **IMPORTANT LEGAL DISCLAIMER**

**This software is provided for educational and research purposes only. Using automated input assistance in Counter-Strike 2 may violate Valve's Terms of Service and could result in a VAC (Valve Anti-Cheat) ban. Use at your own risk and responsibility. The developers are not responsible for any consequences arising from the use of this software.**

---

## 🎯 **Key Features**

### **Multi-Weapon Support**
- **16 Weapon Patterns**: Comprehensive recoil patterns for all major automatic weapons
- **Precise Compensation**: CSV-based pattern storage with millimeter accuracy
- **Customizable Parameters**: Per-weapon timing, sensitivity, and adjustment factors

### **Game State Integration (GSI)**
- **Automatic Weapon Detection**: Real-time weapon identification via CS2's built-in GSI
- **Seamless Transitions**: Instant pattern switching when changing weapons
- **Low Ammo Notifications**: Configurable threshold warnings
- **Real-time Monitoring**: Live game state tracking and response

### **Advanced User Interface**
- **PyQt5 GUI**: Modern, intuitive interface with tabbed configuration
- **Pattern Visualization**: Built-in recoil pattern display and analysis
- **Real-time Status**: Live feedback on system state and active weapon
- **Configuration Management**: Easy adjustment of all system parameters

### **Audio Feedback System**
- **Text-to-Speech (TTS)**: Contextual audio feedback for system events
- **Priority-based Announcements**: Critical alerts take precedence
- **Weapon Change Notifications**: Optional audio confirmation of weapon switches
- **Error Reporting**: Audible alerts for system errors or failures

### **Hotkey Control System**
- **Global Hotkeys**: System-wide keyboard shortcuts (INSERT, HOME, END)
- **Instant Toggle**: Quick enable/disable of recoil compensation
- **Weapon Detection Control**: Manual override of automatic detection
- **Emergency Exit**: Immediate system shutdown capability

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
└── data/                           # Data repositories and persistence
    ├── config_repository.py         # Configuration file management
    └── csv_repository.py            # Pattern data loading and parsing
```

---

## 🔧 **Installation & Setup**

### **System Requirements**
- **Operating System**: Windows 10/11 (required for pywin32)
- **Python**: Version 3.8 or higher
- **Counter-Strike 2**: Latest version with GSI capability
- **Administrative Privileges**: May be required for input simulation

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

3. **Configure Counter-Strike 2 GSI**

   Create a GSI configuration file in your CS2 config directory:
   ```
   Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\cfg\gamestate_integration_artanis.cfg
   ```

   With the following content:
   ```cfg
    "Artanis RCS Integration"
    {
        "uri"                    "http://127.0.0.1:59873"
        "timeout"                "5.0"
        "buffer"                 "0.1"
        "throttle"               "0.1"
        "heartbeat"              "30.0"
        "data"
        {
            "provider"                 "1"      // Game version info
            "map"                      "1"      // Map information
            "round"                    "1"      // Round information
            "player_id"                "1"      // Player identification
            "player_state"             "1"      // Health, armor, flashing, etc.
            "player_weapons"           "1"      // Weapon information (CRITICAL)
            "player_match_stats"       "1"      // Match statistics
            "allplayers_id"            "0"      // Other players (not needed)
            "allplayers_state"         "0"      // Other players state (not needed)
            "allplayers_weapons"       "0"      // Other players weapons (not needed)
            "allplayers_match_stats"   "0"      // Other players stats (not needed)
            "allplayers_position"      "0"      // Other players position (not needed)
            "allgrenades"              "0"      // Grenade information (not needed)
            "bomb"                     "0"      // Bomb information (not needed)
            "phase_countdowns"         "0"      // Phase countdowns (not needed)
            "player_position"          "0"      // Player position (not needed)
        }
    }
   ```

4. **Launch the Application**
   ```bash
   python main.py
   ```

   Or double-click `start.bat` for automated dependency management.

---

## 📋 **Supported Weapons**

The system includes precise recoil patterns for 16 automatic weapons:

### **Assault Rifles**
- **AK-47**
- **M4A4**
- **M4A1-S**
- **Galil AR**
- **FAMAS**
- **SG 553**
- **AUG**

### **Submachine Guns**
- **P90**
- **PP-Bizon**
- **UMP-45**
- **MAC-10**
- **MP5-SD**
- **MP7**
- **MP9**

### **Machine Guns & Pistols**
- **M249**
- **CZ75-Auto**

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
    "tts_enabled": true,          // Enable/disable audio feedback
    "input_souris": "sendinput"   // Input method (SendInput API)
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
    "transition_delay": 0.2,            // Weapon switch delay
    "startup_grace_period": 3.0,        // Initial startup delay
    "require_user_initiation": true,    // Manual activation required
    "announce_weapon_changes": false    // TTS weapon announcements
}
```

#### **Hotkey Bindings**
```json
"hotkeys": {
    "exit": "END",                      // Emergency exit
    "toggle_recoil": "INSERT",          // Toggle compensation on/off
    "toggle_weapon_detection": "HOME"   // Toggle automatic detection
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

## 🔬 **Pattern System**

### **CSV Format Structure**
Each weapon pattern is stored as a CSV file with the format:
```
x_offset, y_offset, timing_ms
0, 0, 30
0.10497, -26.00426, 99
-2.49497, -29.9552, 99
```

### **Pattern Customization**
1. Navigate to the `patterns/` directory
2. Edit the appropriate weapon CSV file
3. Modify compensation values as needed
4. Reload the application to apply changes

### **Pattern Visualization**
The built-in visualization tab display the recoil pattern trajectory

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
- Verify Windows Speech Platform components (English Text To Speech)
- Test TTS by toggling `tts_enabled` setting or via the UI

#### **Sensitivity Calibration**
- Match `game_sensitivity` exactly to CS2 setting
- Adjust weapon-specific multipliers if needed

### **Log Files**
- `recoil_system.log`: Main application log
- `startup.log`: Startup script log (from start.bat)

---

## 🔧 **Advanced Configuration**

### **Timing Parameter Explanation**
- **multiple**: Overall compensation strength multiplier
- **sleep_divider**: Controls timing between compensation adjustments
- **sleep_suber**: Fine-tuning for timing intervals

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

### **Testing Requirements**
- Test all weapon patterns for accuracy
- Verify GSI integration functionality
- Validate hotkey system operation
- Confirm TTS system reliability

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
- [CS2 GSI Implementation Guide](https://github.com/antonpup/CounterStrike2GSI)

---

## 📄 **License & Attribution**

### **License**
This project is released under the MIT License with the following additional terms:

**EDUCATIONAL USE ONLY**: This software is intended solely for educational and research purposes. Any use in violation of game Terms of Service is strictly prohibited and not endorsed by the developers.

### **Third-Party Acknowledgments**
- **PyQt5**: GUI framework by Riverbank Computing
- **matplotlib**: Plotting library by the Matplotlib Development Team
- **numpy**: Numerical computing library by NumPy Developers
- **pywin32**: Windows API access by Mark Hammond

### **Pattern and algorithms Data Sources**
Recoil patterns derived from CS2 chinese community.
Algorithms derived from this project [ NewTennng / csgoPress-the-gun](https://github.com/NewTennng/csgoPress-the-gun/tree/main)