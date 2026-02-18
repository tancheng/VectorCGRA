import pathlib

# For easier A/B test
p = pathlib.Path('/home/jackcui/Arch/Validation_CaseStudy/VectorCGRA/validation/test/sig1')
s = p.read_text()

def pretty_bracket_text(s: str, indent_unit: str = '  ') -> str:
    out = []
    indent = 0
    for ch in s:
        if ch in '])':
            indent = max(indent-1, 0)
            out.append('\n' + indent_unit*indent + ch)
        elif ch in '[(':
            out.append(ch)
            indent += 1
            out.append('\n' + indent_unit*indent)
        elif ch == ',':
            out.append(ch + '\n' + indent_unit*indent)
        else:
            out.append(ch)
    return ''.join(out)

formatted = pretty_bracket_text(s)
out_path = p.with_suffix(p.suffix + '.pretty')
out_path.write_text(formatted)
print(f'Wrote: {out_path}')



# replicate for sig2

p = pathlib.Path('/home/jackcui/Arch/Validation_CaseStudy/VectorCGRA/validation/test/sig2')
s = p.read_text()

def pretty_bracket_text(s: str, indent_unit: str = '  ') -> str:
    out = []
    indent = 0
    for ch in s:
        if ch in '])':
            indent = max(indent-1, 0)
            out.append('\n' + indent_unit*indent + ch)
        elif ch in '[(':
            out.append(ch)
            indent += 1
            out.append('\n' + indent_unit*indent)
        elif ch == ',':
            out.append(ch + '\n' + indent_unit*indent)
        else:
            out.append(ch)
    return ''.join(out)

formatted = pretty_bracket_text(s)
out_path = p.with_suffix(p.suffix + '.pretty')
out_path.write_text(formatted)
print(f'Wrote: {out_path}')




# replicate for sig2

p = pathlib.Path('/home/jackcui/Arch/Validation_CaseStudy/VectorCGRA/validation/test/sig3')
s = p.read_text()

def pretty_bracket_text(s: str, indent_unit: str = '  ') -> str:
    out = []
    indent = 0
    for ch in s:
        if ch in '])':
            indent = max(indent-1, 0)
            out.append('\n' + indent_unit*indent + ch)
        elif ch in '[(':
            out.append(ch)
            indent += 1
            out.append('\n' + indent_unit*indent)
        elif ch == ',':
            out.append(ch + '\n' + indent_unit*indent)
        else:
            out.append(ch)
    return ''.join(out)

formatted = pretty_bracket_text(s)
out_path = p.with_suffix(p.suffix + '.pretty')
out_path.write_text(formatted)
print(f'Wrote: {out_path}')
