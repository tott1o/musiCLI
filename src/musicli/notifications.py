"""
Robust Windows Toast notification utility for MusiCLI.
"""

import subprocess
import threading
import os


def show_desktop_notification(title: str, message: str, image_path: str = None) -> None:
    """Show a modern Windows Toast notification using a robust PowerShell script."""
    
    def run_notification():
        # Clean text for XML/PowerShell - escape single quotes and special XML chars
        s_title = title.replace("'", "''").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s_msg = message.replace("'", "''").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Build XML for the toast
        # We use a simpler template first to ensure it appears
        img_xml = f'<image placement="appLogoOverride" src="{image_path}"/><image src="{image_path}"/>' if image_path else ""
        xml = f'<toast><visual><binding template="ToastGeneric"><text>{s_title}</text><text>{s_msg}</text>{img_xml}</binding></visual></toast>'
        
        # This script is more compatible with different PowerShell versions
        ps_script = f"""
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml('{xml}')
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        
        # Try a few different common AppIDs
        $appIds = @(
            "{{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}}\\WindowsPowerShell\\v1.0\\powershell.exe",
            "Microsoft.Explorer.Notification",
            "MusiCLI"
        )
        
        foreach ($appId in $appIds) {{
            try {{
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
                break
            }} catch {{
                continue
            }}
        }}
        """
        
        try:
            # We use -ExecutionPolicy Bypass to ensure it runs
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except Exception:
            pass

    threading.Thread(target=run_notification, daemon=True).start()
