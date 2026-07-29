from typing import Any


class BrandingManager:
    def __init__(self):
        self.defaults = {
            "logo_url": "https://cdn-icons-png.flaticon.com/512/4712/4712035.png",
            "primary_color": "#6366f1",
            "app_name": "AIOS Manager",
            "custom_domain": None
        }
    
    def get_workspace_branding(self, workspace_id: str) -> dict[str, Any]:
        """В реальном приложении здесь был бы запрос к БД."""
        return self.defaults
    
    def apply_branding_to_ui(self, workspace_id: str):
        """Применяет кастомные стили NiceGUI."""
        from nicegui import ui
        branding = self.get_workspace_branding(workspace_id)
        
        ui.add_head_html(f"""
        <style>
            :root {{
                --q-primary: {branding['primary_color']} !important;
            }}
            .brand-logo {{
                content: url('{branding['logo_url']}');
                max-height: 40px;
            }}
        </style>
        """)

branding_manager = BrandingManager()
