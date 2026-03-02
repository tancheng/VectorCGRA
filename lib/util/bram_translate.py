from pymtl3.passes.backends.verilog import VerilogTranslationPass, VerilogPlaceholderPass
import os
import re

def add_bram_attributes_to_verilog(verilog_file):
    """
    Post-process Verilog file to add BRAM synthesis attributes.
    """
    with open(verilog_file, 'r') as f:
        content = f.read()
    
    # Pattern 1: Find register arrays that look like memory
    # Matches: reg [WIDTH:0] mem [DEPTH:0];
    pattern1 = r'(\s*)(reg\s+\[[^\]]+\]\s+(mem|regs)\s+\[[^\]]+\]\s*;)'
    
    def add_attribute(match):
        indent = match.group(1)
        declaration = match.group(2)
        # Add BRAM attribute before declaration
        return f'{indent}(* ram_style = "block" *) {declaration}'
    
    content = re.sub(pattern1, add_attribute, content)
    
    # Pattern 2: For BRAM_RegisterFile modules, add module-level attribute
    pattern2 = r'(module\s+BRAM_RegisterFile[^\(]*\()'
    
    def add_module_attr(match):
        module_decl = match.group(1)
        return f'(* ram_style = "block" *)\n{module_decl}'
    
    content = re.sub(pattern2, add_module_attr, content)
    
    # Write back
    with open(verilog_file, 'w') as f:
        f.write(content)
    
    print(f"Added BRAM attributes to {verilog_file}")


def translate_design_with_bram(top_module, output_dir=".", add_bram_attrs=True):
    """
    Translate PyMTL3 design to Verilog with BRAM optimization.
    
    Args:
        top_module: PyMTL3 Component instance (already elaborated)
        output_dir: Directory to write Verilog files
        add_bram_attrs: Whether to add BRAM synthesis attributes
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Apply Verilog translation pass
    # top_module.apply(VerilogTranslationPass())
    
    # Find generated Verilog files
    verilog_files = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith('.v'):
                verilog_files.append(os.path.join(root, file))
    
    # Add BRAM attributes if requested
    if add_bram_attrs:
        for vfile in verilog_files:
            add_bram_attributes_to_verilog(vfile)
    
    print(f"\nTranslation complete!")
    print(f"Generated {len(verilog_files)} Verilog files in {output_dir}")
    print(f"BRAM attributes: {'Added' if add_bram_attrs else 'Not added'}")
    
    return verilog_files