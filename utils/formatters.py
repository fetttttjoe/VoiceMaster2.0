import re
from typing import Any


def format_template(template: str, **kwargs: Any) -> str:
    """
    Safely formats a string template with nested attributes using keyword arguments.

    This function allows for dynamic string formatting where placeholders can
    represent attributes of objects passed as keyword arguments. For example,
    `"{ctx.author.name}"` will resolve to `ctx_object.author.name` if `ctx=ctx_object`
    is passed in `kwargs`. It gracefully handles missing attributes or objects
    by returning the original placeholder, preventing `AttributeError` exceptions.

    Example Usage:
        `format_template("User: {ctx.author.name} entered channel {channel.name}", ctx=ctx_object, channel=channel_object)`

    Args:
        template: The string template containing placeholders like `{obj.attr.nested_attr}`.
        **kwargs: Keyword arguments where keys are object names (e.g., `ctx`, `member`)
                  and values are the corresponding objects (e.g., `commands.Context`, `discord.Member`).

    Returns:
        The formatted string with placeholders replaced by their resolved values.
        If a placeholder or its nested attribute cannot be resolved, the original
        placeholder string (e.g., "{ctx.author.name}") is kept in the output.
    """

    def get_value(obj: Any, attr_string: str) -> Any:
        """
        Recursively retrieves a nested attribute's value from an object.

        Args:
            obj: The base object (e.g., `ctx`).
            attr_string: A dot-separated string of attributes (e.g., `author.name`).

        Returns:
            The value of the nested attribute, or `None` if any part of the path is missing.
        """
        current_obj = obj
        for attr in attr_string.split("."):
            # Use getattr with a default of None to prevent AttributeError
            current_obj = getattr(current_obj, attr, None)
            if current_obj is None:
                return None  # Return None if any attribute in the chain is not found
        return current_obj

    # Find all placeholders enclosed in curly braces, e.g., {ctx.author.name}
    placeholders = re.findall(r"\{(.+?)\}", template)

    for placeholder in placeholders:
        # Split the placeholder into the initial object name and its subsequent attributes
        # Example: "ctx.author.name" -> ["ctx", "author.name"]
        parts = placeholder.split(".", 1)
        obj_name = parts[0]

        # Check if the initial object name exists in the provided keyword arguments
        if obj_name in kwargs:
            obj = kwargs[obj_name]

            # If there are nested attributes to access (e.g., 'author.name')
            if len(parts) > 1:
                attr_string = parts[1]
                value = get_value(obj, attr_string)
            else:
                # The placeholder refers directly to the object itself (e.g., "{member}")
                value = obj

            # If a valid value was retrieved (not None after traversal)
            if value is not None:
                # Replace the original placeholder with the string representation of the value
                template = template.replace(f"{{{placeholder}}}", str(value))
            else:
                # If the value could not be resolved (e.g., attribute missing),
                # leave the placeholder as is (or replace with a default like 'N/A' if preferred).
                # For this implementation, the original placeholder is kept.
                pass  # No replacement if value is None
        # If the top-level object (obj_name) is not in kwargs, the placeholder remains unchanged.

    return template
