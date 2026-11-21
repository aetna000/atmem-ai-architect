from pathlib import Path
import base64
from strands.tools import tool

@tool
def write_file(filename: str, content: str, is_binary: bool = False, architecture_name: str = None) -> str:
    """
    Write content to output directory with deterministic file handling
    
    Args:
        filename: Name of file to create (e.g., 'diagram.png', 'report.pdf')
        content: File content (text string or base64-encoded binary)
        is_binary: True for images/PDFs, False for text files
        architecture_name: Optional architecture name for subdirectory
    
    Returns:
        Success message with absolute file path
    """
    # Create base output directory using absolute path
    output_dir = Path.cwd() / "generated-diagrams"
    
    # Add architecture subdirectory if provided
    if architecture_name:
        # Strict filesystem naming: only alphanumeric and hyphens, max 30 chars
        clean_name = "".join(c for c in architecture_name if c.isalnum() or c == '-')
        clean_name = clean_name.lower().strip('-')[:30]
        if not clean_name:
            clean_name = "architecture"
        output_dir = output_dir / clean_name
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / filename
    
    if is_binary:
        # Handle binary files (images, PDFs) - decode base64 content
        binary_content = base64.b64decode(content)
        file_path.write_bytes(binary_content)
    else:
        # Handle text files (JSON, YAML, Markdown, etc.)
        file_path.write_text(content, encoding='utf-8')
    
    return f"File saved: {file_path.absolute()}"
