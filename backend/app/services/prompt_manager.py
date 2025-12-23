import os
from pathlib import Path

class PromptManager:
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self.templates = {}
        self._load_templates()

    def _load_templates(self):
        """Load all markdown templates from the prompts directory."""
        for prompt_file in self.prompts_dir.glob("*.md"):
            with open(prompt_file, "r") as f:
                self.templates[prompt_file.stem] = f.read()

    def get_template(self, template_name: str) -> str:
        """Get a specific template by name."""
        return self.templates.get(template_name, self.templates.get("default"))

    def determine_intent(self, question: str) -> str:
        """Determine the intent of the question to select the best template."""
        q = question.lower()
        
        # Comparison Intent
        if any(x in q for x in [" vs ", "compare", "difference", "better", "between", "versus"]):
            return "comparison"
        
        # Troubleshooting Intent
        if any(x in q for x in ["broken", "not working", "fix", "error", "issue", "problem", "fail", "help with", "how to fix"]):
            return "troubleshooting"
        
        # Specifications Intent
        if any(x in q for x in ["specs", "specifications", "weight", "dimensions", "power", "voltage", "channels", "inputs", "outputs"]):
            return "specs"
            
        # List Products Intent
        if any(x in q for x in ["list", "show", "what", "which", "all"]) and any(x in q for x in ["products", "models", "items", "inventory", "catalog", "series", "available"]):
            return "list_products"

        return "default"

prompt_manager = PromptManager()
