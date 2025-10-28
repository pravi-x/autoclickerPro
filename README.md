# autoclickerPro

An automation tool that simulates right-clicks at chosen pixels, monitors color changes to trigger complex sequences of clicks and movements, and allows users to start these sequences with a hotkey. Actions can be grouped, saved, and reloaded from CSV files for easy reuse.

## Features

🎯 Pixel-based right-click simulation – perform clicks at exact screen coordinates.

🎨 Pixel color monitoring – track color changes to trigger automated actions.

🔁 Custom action sequences – chain movements, clicks, and conditions into complex workflows.

⌨️ Hotkey support – instantly start saved sequences with a keyboard shortcut.

💾 Save & reuse actions – group actions into reusable sets.

📂 CSV integration – export and import sequences for easy sharing and reloading.

## Installation

```
# Clone this repository
git clone https://github.com/pravi-x/autoclickerPro.git

# Navigate into the folder
cd autoclickerPro

# Install the requirements
pip install -r requirements.txt

# Run the app
python main.py
```

## Building an Executable

```
pip install pyinstaller
run: pyinstaller --onefile --noconsole --name "AutoClicker" --icon icon.ico --version-file version_info.txt main.py

```

### or with github actions

```
git tag v1.1 && git push origin v1.1
```

The executable will be available in the `dist/` folder
