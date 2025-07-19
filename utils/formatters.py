# VoiceMaster2.0/utils/formatters.py
import re

def format_template(template: str, **kwargs) -> str:
    """
    Safely formats a string template with nested attributes.
    Example: format_template("User: {ctx.author.name}", ctx=ctx_object)
    """
    def get_value(obj, attr_string):
        for attr in attr_string.split('.'):
            obj = getattr(obj, attr, None)
            if obj is None:
                return f"{{{attr_string}}}" # Return placeholder if not found
        return obj

    # Find all placeholders like {ctx.author.name}
    placeholders = re.findall(r"\{(.+?)\}", template)

    for placeholder in placeholders:
        # Split obj name and its attributes (e.g., 'ctx' and 'author.name')
        parts = placeholder.split('.', 1)
        obj_name = parts[0]
        
        if obj_name in kwargs:
            obj = kwargs[obj_name]
            # If there are attributes to access
            if len(parts) > 1:
                attr_string = parts[1]
                value = get_value(obj, attr_string)
            else: # The placeholder is the object itself
                value = obj
            
            template = template.replace(f"{{{placeholder}}}", str(value))

    return template
