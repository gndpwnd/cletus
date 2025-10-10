"""
css_loader.py
Dynamic CSS file loader for Jinja2 templates
Place this in your project root or in a utils folder
"""
from pathlib import Path
from typing import List

class CSSLoader:
    """Automatically discover and order CSS files for inclusion"""
    
    # Define the desired loading order
    CSS_ORDER = [
        "variables.css",
        "reset.css",
        "typography.css",
        "layout.css",
        "navigation.css",
        "components.css",
        "tables.css",
        "articles.css",
        "scraper.css",
        "analysis.css",
        "blacklist.css",
        "utilities.css",
        "animations.css",
        "responsive.css",
    ]
    
    def __init__(self, css_directory: str = "static/css"):
        self.css_dir = Path(css_directory)
    
    def get_css_files(self) -> List[str]:
        """
        Get all CSS files in the correct order
        Returns list of paths relative to static directory
        """
        css_files = []
        
        # Add files in the defined order if they exist
        for filename in self.CSS_ORDER:
            filepath = self.css_dir / filename
            if filepath.exists():
                css_files.append(f"css/{filename}")
        
        # Add any remaining CSS files not in the order list
        # (except main.css and component.css which are deprecated)
        for filepath in self.css_dir.glob("*.css"):
            filename = filepath.name
            if filename not in self.CSS_ORDER and filename not in ["main.css", "component.css"]:
                css_files.append(f"css/{filename}")
        
        return css_files
    
    def get_css_links(self) -> str:
        """
        Generate HTML link tags for all CSS files
        """
        css_files = self.get_css_files()
        links = []
        
        for css_file in css_files:
            links.append(f'<link rel="stylesheet" href="/static/{css_file}">')
        
        return "\n    ".join(links)


# Create a singleton instance
css_loader = CSSLoader()


def get_css_files() -> List[str]:
    """Convenience function to get CSS files"""
    return css_loader.get_css_files()


def get_css_links() -> str:
    """Convenience function to get CSS link tags"""
    return css_loader.get_css_links()